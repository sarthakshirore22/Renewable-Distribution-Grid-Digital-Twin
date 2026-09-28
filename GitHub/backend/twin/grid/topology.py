import networkx as nx
import pandapower.topology as top

def is_radial_ok(net) -> bool:
    """
    Check if the network is radial and connected using networkx.
    A network is radial if it is connected and has exactly nodes - 1 edges.
    """
    g = top.create_nxgraph(net)
    
    # Check connectivity
    if not nx.is_connected(g):
        return False
        
    # Check radiality
    num_nodes = g.number_of_nodes()
    num_edges = g.number_of_edges()
    
    return num_edges == num_nodes - 1
