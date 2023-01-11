from __future__ import absolute_import, division, print_function

__metaclass__ = type
import os
import queue

import graphviz
import yaml

DEFAULT_COLUMN_BLOCK = 7
DEFAULT_ROW_BLOCK = 4
BORDER_VALUE = 0
HEIGHT_VALUE = 20
WIDTH_VALUE = 14
NODE_HEIGHT_VALUE = 70
NODE_WIDTH_VALUE = 40

def read_yaml_file(filename):
    """
    Open a structure config file and load a data from the file

    Args:
        filename: Name of the file

    Returns:
        Data from the file
    """
    with open(filename, "r", encoding="utf-8") as stream:
        data = None
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
        return data


def create_node_dict(file_data, filename):
    """
    Create a dictionary of nodes with its corresponding neighbours

    Args:
        file_data: Data of structure config file
        filename: Name of the file

    Returns:
        Dictionary with node and its corresponding neighbours
    """
    node_dict = {}
    node_dict["name"] = os.path.splitext(filename)[0].split("/")[-1]
    node_dict["neighbours"] = []
    if file_data and file_data.get("ethernet_interfaces"):
        for key, value in file_data["ethernet_interfaces"].items():
            neighbour_dict = {}
            neighbour_dict["neighborDevice"] = value["peer"]
            neighbour_dict["neighborPort"] = value["peer_interface"]
            neighbour_dict["port"] = key
            if "channel_group" in value and "id" in value["channel_group"]:
                neighbour_dict["portChannel"] = value["channel_group"]["id"]
            node_dict["neighbours"].append(neighbour_dict)        
    return node_dict


def structured_config_to_topology_input(output_list, node_dict, diagram_groups, current_dict=None):
    """
    Convert structure config file data to topology input data by creating a nested dictionary
    of "nodes" and "groups"

    Args:
        output_list: Original input dictionary with nested "name", "nodes" and "groups" keys
        node_dict: List of nodes
        node_neighbour_dict: Dictionary with nodes and neighbours list
                       ex- {'0': ['super-spine1', 'super-spine2']}
    Returns:
       output_list: List of dictionary with nested "name", "nodes" and "groups" keys
    """

    if diagram_groups:
        diagram_group_var = diagram_groups.pop(0)
        for temp_check in diagram_group_var.keys():
            if temp_check in ['fabric_name','dc_name','pod_name','name']:
                diagram_group_var = diagram_group_var[temp_check] 

        if not output_list:
            new_dict = {"name": diagram_group_var, "groups": [], "nodes": []}
            output_list.append(new_dict)
            structured_config_to_topology_input(new_dict["groups"], node_dict, diagram_groups, new_dict)
        else:
            found = False
            for entry in output_list:
                if diagram_group_var == entry["name"]:
                    structured_config_to_topology_input(entry["groups"], node_dict, diagram_groups, entry)
                    found = True     

            if not found:
                new_dict = {"name": diagram_group_var, "groups": [], "nodes": []}
                output_list.append(new_dict)
                structured_config_to_topology_input(new_dict["groups"], node_dict, diagram_groups, new_dict)
    else:
        current_dict["nodes"].append(node_dict)

    return output_list


def find_root_nodes(data, root=None):
    """
    Find a root node

    Args:
        data: Dictinary with nested keys "nodes" and "groups"

    Returns:
        Return a dictinary with root node as "0" with it's neighbours
    """

    if not root:
        root = {"name": "0", "neighbours": []}
    if "nodes" in data and data["nodes"]:
        for node in data["nodes"]:
            neighbour_dict = {"neighborDevice": node["name"], "neighborPort": "", "port": ""}
            root["neighbours"].append(neighbour_dict)
        return root

    if "groups" in data and data["groups"]:
        for group in data["groups"]:
            root = find_root_nodes(group, root)
        return root


def create_graph_dict(output_list, inventory_group, nodes=None, node_neighbour_dict=None):
    """
    Create a dictionary of rank/levels and it's corresponding node list

    Args:
      output_list: List of dictionaries with nested "name", "nodes" and "groups" keys
      nodes: List of nodes
      node_neighbour_dict: Dictionary with nodes and neighbours list
                        ex- {'0': ['super-spine1', 'super-spine2']}
    Returns:
       nodes: List of nodes which are present in the graph
       node_neighbour_dict: Dictionary of node and its corresponding neighbours
    """
    if nodes is None:
        nodes = []
    if node_neighbour_dict is None:
        node_neighbour_dict = {}
    for group in output_list:
        if "nodes" in list(group.keys()) and group["nodes"]:
            for node in group["nodes"]:
                if  (node["name"] in inventory_group) or (node["name"] == "0"):
                    nodes.append(node["name"])
                    neighbours = []
                    for neighbour in node["neighbours"]:
                        if  neighbour["neighborDevice"] in inventory_group:  
                            node_detail_dict = {}

                            if len(neighbour["port"]) == 10 and len(neighbour["port"]) != 0:
                                node_detail_dict["nodePort"] = neighbour["port"][8:10]

                            if len(neighbour["port"]) == 9 and len(neighbour["port"]) != 0:
                                node_detail_dict["nodePort"] = neighbour["port"][8]

                            if len(neighbour["port"]) < 9:
                                node_detail_dict["nodePort"] = ""

                            node_detail_dict["neighborDevice"] = neighbour["neighborDevice"]

                            if len(neighbour["neighborPort"]) == 10 and len(neighbour["neighborPort"]) != 0:
                                node_detail_dict["neighborPort"] = neighbour["neighborPort"][8:10]

                            if len(neighbour["neighborPort"]) == 9 and len(neighbour["neighborPort"]) != 0:
                                node_detail_dict["neighborPort"] = neighbour["neighborPort"][8]

                            if len(neighbour["neighborPort"]) < 9:
                                node_detail_dict["neighborPort"] = ""

                            # neighbours.append(neighbour['neighborDevice'])
                            neighbours.append(node_detail_dict)   
                    node_neighbour_dict[node["name"]] = neighbours
        if "groups" in group and group["groups"]:
            create_graph_dict(group["groups"], inventory_group, nodes, node_neighbour_dict)
     
    return nodes, node_neighbour_dict


def find_node_levels(graph, start_node, node_list):

    """
    Function to determine level of each node starting from start_node using BFS algorithm
    Args:
        graph: dictionary with node and its neighbours list
        start_node: Starting point/root node of the graph
        node_list: List of nodes
    Returns:
         dict: Return a dictionary with level as key and node list as value
    """
    # array to store level of each node
    node_level_dict = {}
    marked = {node: False for node in node_list}

    # create a queue
    que = queue.Queue()
    # enqueue element x
    que.put(start_node)
    # initialize level of start_node
    # node to 0
    node_level_dict[start_node] = 0
    # marked it as visited
    marked[start_node] = True

    # do until queue is empty
    while not que.empty():
        # get the first element of queue
        start_node = que.get()       
        # traverse neighbors of node start_node
        if start_node in graph:
            for i in graph[start_node]:
                # neighbor is neighbor of node start_node
                neighbor = i["neighborDevice"]                            
                # if neighbor is not marked already
                if neighbor in marked.keys() and not marked[neighbor]:
                    # enqueue neighbor in queue
                    que.put(neighbor)
                    # level of neighbor is level of start_node + 1
                    node_level_dict[neighbor] = node_level_dict[start_node] + 1
                    # mark neighbor
                    marked[neighbor] = True

    level_dict = {}
    for node, level in node_level_dict.items():
        if level not in level_dict:
            level_dict[level] = [node]
        else:
            level_dict[level].append(node)

    return level_dict, node_level_dict


def draw_nested_subgraphs(input_data, level_dict, graph_obj, undefined_rank_nodes, node_port_val, column_num, row_num, pod_conn):
    """
    Create a nested subgraphs recursively based on input_data

    Args:
        input_data: Original input dictionary with nested "name", "nodes" and "groups" keys
        level_dict: Node level dictionary
        graph_obj: Object of graphviz.Graph class
        undefined_rank_nodes: Nodes without parent/root nodes
    Returns:
         None
    """

    for data in input_data:
        graph_obj.attr(ranksep="0.7")
        with graph_obj.subgraph(name="cluster_child_" + str(data["name"])) as subgraph:
            subgraph.attr(label=data["name"])
            subgraph.attr(labelloc="t")

            if "nodes" in data and data["nodes"]:
                pod_node_list = [node["name"] for node in data["nodes"] if node["name"] != "0"]
                new_rank_dict = {"undefined": {}}
                new_node_list = [undefined_rank_node for undefined_rank_node in undefined_rank_nodes if undefined_rank_node in pod_node_list]
                new_rank_dict["undefined"] = new_node_list
                for rank, nodes in level_dict.items():
                    new_rank_dict[rank] = []
                    for node in nodes:
                        if node in pod_node_list and node not in undefined_rank_nodes:
                            new_rank_dict[rank].append(node)

                for rank, nodes in new_rank_dict.items():
                    if nodes:
                        if rank not in pod_conn.keys():
                            pod_conn[rank] = [nodes]
                        else:
                            pod_conn[rank] = pod_conn[rank] + [nodes]        


                for rank, nodes in new_rank_dict.items():
                    if nodes:
                        with subgraph.subgraph() as inner_subgraph:
                            inner_subgraph.attr(rank="same")
                            # inner_subgraph.attr(rankdir="LR")
                            for node in nodes:
                                if node not in undefined_rank_nodes:
                                    node_ports = node_port_val[node]

                                    node_table = '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
                                    if (len(node_ports["top"]) == 0) and (len(node_ports["bottom"]) == 0) and (len(node_ports["left"]) == 0) and (len(node_ports["right"]) == 0):
                                        # node_table = node_table + "<TR>"
                                        node_table = f"{str(node_table)} <TR><TD HEIGHT=\"{str(NODE_HEIGHT_VALUE)}\" WIDTH=\"{str(NODE_WIDTH_VALUE)}\" BGCOLOR=\"#4a69bd\"> <FONT COLOR=\"#ffffff\">{node}</FONT></TD></TR>\n"
                                        # node_table = node_table + "</TR>"
                                    else:
                                        # top
                                        port_len = len(node_ports["top"])

                                        # port_len = len(node_ports["top"])
                                        if port_len != 0:
                                            node_table = f"{str(node_table)} <TR>"
                                            port_col = [0] * column_num

                                            # if port_len % 2 != 0:
                                            #     port_start = column_num / (port_len * 2)
                                            # else:
                                            #     if port_len == 0:
                                            #         port_start = column_num / (port_len + 2)
                                            #     else:
                                            #         port_start = column_num / (port_len)

                                            if (column_num%2) == 0:
                                                port_start = (column_num / port_len) - 1 
                                            elif (column_num%2) != 0:
                                                port_start = (column_num / port_len)         

                                            if port_len == 1:
                                                port_start = (column_num - 1) / 2
                                            if port_len == column_num:
                                                port_start = 0

                                            port_start = int(port_start)

                                            node_ports["top"].sort()
                                            for port_pos in range(port_start, port_len + port_start):
                                                port_col[port_pos] = node_ports["top"][port_pos - port_start]

                                            for port_val in port_col:
                                                port_val = str(port_val).replace(" ", "").replace("0", "")
                                                if port_val == 0 or port_val == "":
                                                    node_table = f"{str(node_table)} <TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\" BORDER=\"{str(BORDER_VALUE)}\" ></TD>\n"
                                                else:
                                                    node_table = f"{str(node_table)} <TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\" PORT=\"{str(port_val)}\">{str(port_val)}</TD>\n"

                                            node_table = f"{str(node_table)} </TR>"
                                        else:
                                            node_table = f"{str(node_table)} <TR>"
                                            for td_val in range(column_num):
                                                node_table = f"{str(node_table)} <TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\" BORDER=\"{str(BORDER_VALUE)}\" ></TD>\n"    
                                            node_table = f"{str(node_table)} </TR>"    


                                        #left right
                                        if len(node_ports["left"]) == 0 and len(node_ports["right"]) == 0:
                                            node_table = f"{str(node_table)} <TR><TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\" BORDER=\"{str(BORDER_VALUE)}\" ></TD><TD BGCOLOR=\"#4a69bd\" COLSPAN=\"{str(column_num - 2)}\" ROWSPAN=\"{str(row_num)}\"> <FONT COLOR=\"#ffffff\">{node}</FONT></TD><TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\"  BORDER=\"{str(BORDER_VALUE)}\" ></TD></TR>\n"
                                            for i in range(row_num - 1):
                                                node_table = f"{str(node_table)} <TR><TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\" BORDER=\"{str(BORDER_VALUE)}\" ></TD><TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\" BORDER=\"{str(BORDER_VALUE)}\" ></TD> </TR>\n"
                                        else:
                                            node_table = f"{str(node_table)} <TR><TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\"  BORDER=\"{str(BORDER_VALUE)}\" ></TD><TD BGCOLOR=\"#4a69bd\" COLSPAN=\"{str(column_num - 2)}\" ROWSPAN=\"{str(row_num)}\"> <FONT COLOR=\"#ffffff\">{node}</FONT></TD><TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\"  BORDER=\"{str(BORDER_VALUE)}\" > </TD></TR>\n"

                                            row_port_num = row_num - 2

                                            #left
                                            left_row_val = [0] * row_port_num

                                            row_port_len = len(node_ports["left"])
                                            row_port_start = 0

                                            if row_port_len != 0:
                                                if (row_port_num%2) == 0:
                                                    row_port_start = (row_port_num / row_port_len) - 1 
                                                elif (row_port_num%2) != 0:
                                                    row_port_start = (row_port_num / row_port_len)         

                                                if row_port_len == 1:
                                                    row_port_start = (row_port_num - 1) / 2
                                                if row_port_len == row_port_num:
                                                    row_port_start = 0

                                            row_port_start = int(row_port_start)


                                            node_ports["left"].sort()
                                            for port_pos in range(row_port_start, row_port_len + row_port_start):
                                                left_row_val[port_pos] = node_ports["left"][port_pos - row_port_start]


                                            #right
                                            right_row_val = [0] * row_port_num

                                            row_port_len = len(node_ports["right"])
                                            row_port_start = 0

                                            if row_port_len != 0:
                                                if (row_port_num%2) == 0:
                                                    row_port_start = (row_port_num / row_port_len) - 1 
                                                elif (row_port_num%2) != 0:
                                                    row_port_start = (row_port_num / row_port_len)         

                                                if row_port_len == 1:
                                                    row_port_start = (row_port_num - 1) / 2
                                                if row_port_len == row_port_num:
                                                    row_port_start = 0

                                            row_port_start = int(row_port_start)

                                            node_ports["right"].sort()
                                            for port_pos in range(row_port_start, row_port_len + row_port_start):
                                                right_row_val[port_pos] = node_ports["right"][port_pos - row_port_start]


                                            # node_ports["top"].sort()
                                            # for port_pos in range(port_start, port_len + port_start):
                                            #     port_col[port_pos] = node_ports["top"][port_pos - port_start]
                                            for row_val in range(row_port_num):
                                                #left
                                                if left_row_val[row_val] == 0: 
                                                    node_table = f"{str(node_table)} <TR><TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\" BORDER=\"{str(BORDER_VALUE)}\" ></TD>\n"
                                                else:
                                                    node_table = f"{str(node_table)} <TR><TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\" PORT=\"{str(left_row_val[row_val])}\">{str(left_row_val[row_val])}</TD>\n"

                                                #right
                                                if right_row_val[row_val] == 0:                                                    
                                                    node_table = f"{str(node_table)} <TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\" BORDER=\"{str(BORDER_VALUE)}\" ></TD></TR>\n"
                                                else:
                                                    node_table = f"{str(node_table)} <TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\" PORT=\"{str(right_row_val[row_val])}\">{str(right_row_val[row_val])}</TD></TR>\n"

                                            node_table = f"{str(node_table)} <TR><TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\"  BORDER=\"{str(BORDER_VALUE)}\"></TD><TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\" BORDER=\"{str(BORDER_VALUE)}\"></TD></TR>\n"

                                        # bottom
                                        port_len = len(node_ports["bottom"])
                                        if port_len != 0:
                                            node_table = f"{str(node_table)} <TR>"

                                            port_col = [0] * column_num

                                            # if port_len % 2 != 0:
                                            #     port_start = column_num / (port_len * 2)
                                            # else:
                                            #     if port_len == 0:
                                            #         port_start = column_num / (port_len + 2)
                                            #     else:
                                            #         port_start = column_num / (port_len)



                                            if (column_num%2) == 0:
                                                port_start = (column_num / port_len) - 1 
                                            elif (column_num%2) != 0:
                                                port_start = (column_num / port_len)         

                                            if port_len == 1:
                                                port_start = (column_num - 1) / 2
                                            if port_len == column_num:
                                                port_start = 0


                                            port_start = int(port_start)

                                            node_ports["bottom"].sort()
                                            for port_pos in range(port_start, port_len + port_start):
                                                port_col[port_pos] = node_ports["bottom"][port_pos - port_start]

                                            for port_val in port_col:
                                                port_val = str(port_val).replace(" ", "").replace("0", "")
                                                if port_val == 0 or port_val == "":
                                                    node_table = f"{str(node_table)} <TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\" BORDER=\"{str(BORDER_VALUE)}\" ></TD>\n"
                                                else:
                                                    node_table = f"{str(node_table)} <TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\" PORT=\"{str(port_val)}\">{str(port_val)}</TD>\n"
                                            node_table = f"{str(node_table)} </TR>"
                                        else:
                                            node_table = f"{str(node_table)} <TR>"
                                            for td_val in range(column_num):
                                                node_table = f"{str(node_table)} <TD HEIGHT=\"{str(HEIGHT_VALUE)}\" WIDTH=\"{str(WIDTH_VALUE)}\" BORDER=\"{str(BORDER_VALUE)}\" ></TD>\n"    
                                            node_table = f"{str(node_table)} </TR>"    

                                    node_table = f"{str(node_table)} </TABLE>>"
                                    node_table = node_table.replace("\n", "")

                                    inner_subgraph.node(node, node_table)

            if "groups" in data and data["groups"]:
                draw_nested_subgraphs(data["groups"], level_dict, subgraph, undefined_rank_nodes, node_port_val, column_num, row_num, pod_conn)


def create_graph_and_set_properties():
    """
    Create a graphviz graph object and set node and edge properties

    Returns: Graph object
    """
    graph_obj = graphviz.Graph(
        name="parent",
        format="svg",
        filename="topology.gv",
        graph_attr={"splines": "false"},
        node_attr={
            "shape": "plaintext",
            "fontsize": " 8pt"
        },
        edge_attr={"fontname": "arial", "fontsize": "6", "center": "true", "concentrate": "true", "minlen": "2", "labelfloat": "false"},
    )
    graph_obj.attr(rank="same")
    # graphviz.layout("neato")
    return graph_obj


def generate_topology(level_dict, node_neighbour_dict, output_list, undefined_rank_nodes, node_port_val):
    """
    Generate topology diagram using graphviz.Graph

    Args:
       level_dict: Dictionary of nodes with respective levels
                  ex- {0: ['0'], 1: ['super-spine1', 'super-spine2']}
       node_neighbour_dict: Dictionary with nodes and neighbours list
                            ex- {'0': ['super-spine1', 'super-spine2']}
       output_list: List of dictionaries with nested "name", "nodes" and "groups" keys
       undefined_rank_nodes: Nodes without parent
    Returns:
        None
    """

    graph_obj = create_graph_and_set_properties()


    column_num = 0
    row_num = 0
    for rank, nodes in level_dict.items():
        for node in nodes:
            node_ports = node_port_val[node]
            column_num = max(column_num, len(node_ports["top"]))
            column_num = max(column_num, len(node_ports["bottom"]))

            row_num = max(row_num, len(node_ports["left"]))
            row_num = max(row_num, len(node_ports["right"]))            


    if column_num == 0 or column_num < DEFAULT_COLUMN_BLOCK:
        column_num = DEFAULT_COLUMN_BLOCK 
    elif column_num >= DEFAULT_COLUMN_BLOCK:
        column_num = column_num + 2

    if row_num <= 1:
        row_num = DEFAULT_ROW_BLOCK
    else:    
        row_num = row_num + 2      

    #to get list of pod conn
    pod_conn = {}
    draw_nested_subgraphs(output_list, level_dict, graph_obj, undefined_rank_nodes, node_port_val, column_num, row_num, pod_conn)

    for node, neighbours in node_neighbour_dict.items():
        if node != "0":
            for neighbour in neighbours:
                if neighbour["nodePort"] != "":
                    node_val = node + ":" + neighbour["nodePort"]
                else:
                    node_val = node

                if neighbour["neighborPort"] != "":
                    neighbour_val = neighbour["neighborDevice"] + ":" + neighbour["neighborPort"]
                else:
                    neighbour_val = neighbour["neighborDevice"]

                temp_diff_pod = []
                for nodes_val in pod_conn.values(): #[['LEAF1', 'LEAF2'], ['LEAF3', 'LEAF4']]
                    if len(nodes_val) > 1:
                        diff_pod = []
                        for pod_node in range(len(nodes_val)):
                            if node in nodes_val[pod_node]:
                                if pod_node not in diff_pod:
                                    diff_pod.append(pod_node) 
                            if neighbour["neighborDevice"] in nodes_val[pod_node]:
                                if pod_node not in diff_pod:
                                    diff_pod.append(pod_node)
                        temp_diff_pod.append(diff_pod)             
        
                flag = False
                for check_len in temp_diff_pod:
                    if len(check_len) > 1:
                        flag = True

                if flag:
                    graph_obj.edge(node_val, neighbour_val, constraint="false", minlen="0")
                else:
                    graph_obj.edge(node_val, neighbour_val)    

                # graph_obj.edge(node_val, neighbour_val)
                
    #print(level_dict)
    # for nodes_val in pod_conn.values():
    #     if len(nodes_val) > 1:
    #         temps = nodes_val
    #         #print(nodes_val)
    #         for idx in range(len(nodes_val)-1):
    #             graph_obj.edge(nodes_val[idx] , nodes_val[idx + 1], constraint="false", style="invis")
    

    graph_obj.view()
