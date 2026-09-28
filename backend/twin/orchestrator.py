from typing import List, Dict, Any, Tuple
from twin.gateway.sensor import TelemetryMessage
from twin.estimation.estimator import build_meas, run_estimation
from twin.forecast.predictor import MockForecaster, analyze_stress
from twin.control.search import find_best_action
import pandapower as pp
import copy

class DigitalTwinOrchestrator:
    def __init__(self, net: pp.pandapowerNet, cfg):
        self.net = net # This is the twin's internal model, updated by estimator
        self.cfg = cfg
        self.forecaster = MockForecaster(cfg, self.net)
        self.current_step = 0
        self.current_state = {}
        
    def tick(self, telemetry: List[TelemetryMessage], step: int) -> Dict[str, Any]:
        """
        Executes one full cycle of the digital twin.
        Returns the estimation results, forecast, and any recommended action.
        """
        self.current_step = step
        
        # 1. State Estimation
        # Provide a default pseudo_variance of 0.1 for the unmeasured buses
        build_meas(self.net, telemetry, pseudo_variance=0.1)
        est_success, conf = run_estimation(self.net)
        
        # If estimation is successful, pandapower updates net.res_bus_est, etc.
        # But we need standard power flow results (net.res_bus) for limits checking and forecasting.
        # So we should run power flow to update net.res_bus using the estimated loads/gens.
        # Wait, the estimated loads/gens are in net.res_load_est and net.res_sgen_est.
        # Let's just run a standard power flow anyway because we just need it to converge for the current_state.
        
        # Extract some state representation
        try:
            pp.runpp(self.net, numba=False)
            self.current_state = {'converged': True, 'vm_pu_mean': self.net.res_bus.vm_pu.mean()}
        except Exception:
            self.current_state = {'converged': False}
            
        # 2. Forecast
        forecast = self.forecaster.predict_window(start_step=self.current_step, window_steps=24)
        
        # 3. Stress Analysis
        is_stressed = analyze_stress(forecast, self.net, self.cfg)
        
        # 4. Search for Control Action
        recommended_action = None
        if is_stressed and est_success and self.current_state.get('converged'):
            recommended_action = find_best_action(self.net, forecast, self.cfg, self.current_state)
            
        return {
            'step': self.current_step,
            'estimation_success': est_success,
            'is_stressed': is_stressed,
            'recommended_action': recommended_action,
            'forecast': forecast
        }
