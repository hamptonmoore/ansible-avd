from __future__ import absolute_import, division, print_function

__metaclass__ = type
import os
import queue

import graphviz
import yaml
import random

import drawSvg as draw

ROUTERSIZE = 120
ROWSPACING = ROUTERSIZE * 2
LVLSPACING = ROUTERSIZE * 2.5
PORTHEIGHT = 30
PORTWIDTH = 20
PORTOFFSET = 3
PORTFONTSIZE = 16

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


def structured_config_to_topology_input(ol, node_dict, diagram_groups, current_dict=None):
    """
    Convert structure config file data to topology input data by creating a nested dictionary
    of "nodes" and "groups"

    Args:
        ol: Original input dictionary with nested "name", "nodes" and "groups" keys
        node_dict: List of nodes
        node_neighbour_dict: Dictionary with nodes and neighbours list
                       ex- {'0': ['super-spine1', 'super-spine2']}
    Returns:
       ol: List of dictionary with nested "name", "nodes" and "groups" keys
    """

    if diagram_groups:
        diagram_group_var = diagram_groups.pop(0)
        for temp_check in diagram_group_var.keys():
            if temp_check in ['fabric_name','dc_name','pod_name','name']:
                diagram_group_var = diagram_group_var[temp_check] 

        if not ol:
            new_dict = {"name": diagram_group_var, "groups": [], "nodes": []}
            ol.append(new_dict)
            structured_config_to_topology_input(new_dict["groups"], node_dict, diagram_groups, new_dict)
        else:
            found = False
            for entry in ol:
                if diagram_group_var == entry["name"]:
                    structured_config_to_topology_input(entry["groups"], node_dict, diagram_groups, entry)
                    found = True     

            if not found:
                new_dict = {"name": diagram_group_var, "groups": [], "nodes": []}
                ol.append(new_dict)
                structured_config_to_topology_input(new_dict["groups"], node_dict, diagram_groups, new_dict)
    else:
        current_dict["nodes"].append(node_dict)

    return ol


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


def create_graph_dict(ol, inventory_group, nodes=None, node_neighbour_dict=None):
    """
    Create a dictionary of rank/levels and it's corresponding node list

    Args:
      ol: List of dictionaries with nested "name", "nodes" and "groups" keys
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
    for group in ol:
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

def generate_topology_hampton(old_level_dict, node_neighbour_dict, ol, undefined_rank_nodes, node_port_val):
    # Weird 0th line they have
    del old_level_dict[0]

    # Make a level loopup dict
    level_dict = {}
    for idx, nodes in old_level_dict.items():
        for node in nodes:
            level_dict[node] = idx

    # print(ol, "\n\n")


    ol = subgroup_inventor_recursive(level_dict, ol[0])
    size = 3000
    d = draw.Drawing(size, size, origin=(0,0), font_family="monospace")
    d.append(draw.Rectangle(0,0,size,size, fill='white'))

    ol = calculate_box_size_recursive(level_dict, ol)

    # print(level_dict)
    print("\n\n")
    print(ol)
    print("\n\n")
    nodes = draw_groups_recursive(d, ol, 20, size-100)

    del node_port_val['0']
    for name, parts in node_port_val.items():
        if name not in nodes:
            continue 
        node = nodes[name]
        node["ports"] = {}
        ox = 0
        for portID in parts["top"]:
            port = {"x": node["x"] - (ROUTERSIZE/2) + ox + (PORTWIDTH/2), "y": node["y"] + (ROUTERSIZE/2) + PORTHEIGHT}
            node["ports"][portID] = port
            d.append(draw.Rectangle(port["x"] - (PORTWIDTH/2), port["y"] - PORTHEIGHT, PORTWIDTH, PORTHEIGHT, fill="white", stroke="black"))
            d.append(draw.Text(portID, PORTFONTSIZE, port["x"], port["y"] - PORTHEIGHT/2 - PORTFONTSIZE/3, fill="black", text_anchor="middle"))
            ox = PORTWIDTH + PORTOFFSET
        
        ox = 0
        for portID in parts["bottom"]:
            port = {"x": node["x"] - (ROUTERSIZE/2) + ox + (PORTWIDTH/2), "y": node["y"] - (ROUTERSIZE/2) - PORTHEIGHT}
            node["ports"][portID] = port
            d.append(draw.Rectangle(port["x"] - (PORTWIDTH/2), port["y"], PORTWIDTH, PORTHEIGHT, fill="white", stroke="black"))
            d.append(draw.Text(portID, PORTFONTSIZE, port["x"], port["y"] + PORTHEIGHT/2 - PORTFONTSIZE/3, fill="black", text_anchor="middle"))
            ox = PORTWIDTH + PORTOFFSET
        
        oy = 0
        for portID in parts["right"]:
            port = {"x": node["x"] + (ROUTERSIZE/2) + PORTHEIGHT, "y": node["y"] + (ROUTERSIZE/2) - PORTHEIGHT - oy + PORTWIDTH}
            node["ports"][portID] = port
            d.append(draw.Rectangle(port["x"] - PORTHEIGHT, port["y"] - PORTWIDTH/2, PORTHEIGHT, PORTWIDTH, fill="white", stroke="black"))
            d.append(draw.Text(portID, PORTFONTSIZE, port["x"] - PORTHEIGHT/2, port["y"] - PORTFONTSIZE/3, fill="black", text_anchor="middle"))
            oy = PORTWIDTH + PORTOFFSET

        oy = 0
        for portID in parts["left"]:
            port = {"x": node["x"] - (ROUTERSIZE/2) - PORTHEIGHT , "y": node["y"] + (ROUTERSIZE/2) - oy - PORTWIDTH/2}
            node["ports"][portID] = port
            d.append(draw.Rectangle(port["x"], port["y"] - (PORTWIDTH/2), PORTHEIGHT, PORTWIDTH, fill="white", stroke="black"))
            d.append(draw.Text(portID, PORTFONTSIZE, port["x"] + PORTHEIGHT/2, port["y"] - PORTFONTSIZE/3, fill="black", text_anchor="middle"))
            oy = PORTWIDTH + PORTOFFSET

    del node_neighbour_dict['0']
    print(node_neighbour_dict)

    for name, links in node_neighbour_dict.items():
        if name not in nodes:
                continue 
        node = nodes[name]["ports"]
        for id, link in enumerate(links):
            if link["neighborDevice"] not in nodes:
                continue
            neigh = nodes[link["neighborDevice"]]["ports"]
            if link["neighborPort"] not in neigh or link["nodePort"] not in node:
                print("MISSING LINK BETWEEN", id, neigh)
                continue
            nol = node[link["nodePort"]]
            nel = neigh[link["neighborPort"]]
            d.append(draw.Line(nol["x"], nol["y"], nel["x"], nel["y"], stroke=f'hsl({random.randint(0,360)},{random.randint(50,100)}%,{random.randint(25,75)}%)', stroke_width=2))


    # Display
    d.setRenderSize(786)
    d.saveSvg('example.svg')

def subgroup_inventor_recursive(ld, ol):
    groupLookup = {}
    if len(ol["groups"]) == 0:
        for idx, child in enumerate(ol["nodes"]):
            if ("." in child["name"] or "0" == child["name"]):
                continue
            lvl = ld[child["name"]]
            if lvl not in groupLookup:
                groupLookup[lvl] = {
                    "nodes": [],
                    "groups": [],
                    "name": child["name"],
                    "psuedo": True,
                }
            groupLookup[lvl]["nodes"].append(child)

        ol["nodes"] = []
        if len(groupLookup.keys()) == 1:
            ol["nodes"] = list(groupLookup.values())[0]["nodes"]
        else:
            keys = list(groupLookup.keys())
            lowest = min(keys)
            keys.remove(lowest)
            secondLowest = min(keys)
            sLI = 0
            other = []
            for i, group in groupLookup.items():
                if i == lowest:
                    ol["nodes"] = group["nodes"]
                elif i == secondLowest:
                    sLI = len(ol["groups"])
                    ol["groups"].append(group)
                else:
                    other.append(group)
            for group in other:
                ol["groups"][sLI]["groups"].append(group)

    for idx, child in enumerate(ol["groups"]):
        child = subgroup_inventor_recursive(ld, child)
        ol["groups"][idx] = child

    return ol

def draw_groups(d, ol, x, y):
    cx = 0
    nodes = {}
    for idx, child in enumerate(ol["groups"]):
        newNodes = draw_groups_recursive(d, child, x + cx, y)
        for k, node in newNodes.items():
            nodes[k] = node
        cx += child["width"]
    
    return nodes

def draw_groups_recursive(d, ol, x, y):
    nodes = {}
    GROUPOFFSET = LVLSPACING
    if len(ol["nodes"]) == 0:
        GROUPOFFSET = 0
    if "psuedo" not in ol:
        d.append(draw.Rectangle(
            x, y-(((ol["height"]-1) * LVLSPACING))-GROUPOFFSET, 
            ol["width"], 
            (((ol["height"]-1) * LVLSPACING))+GROUPOFFSET, 
            stroke="black", fill="white"
            )
        )
        d.append(draw.Text(ol["name"], 24, x+4, y-24, fill="black"))

    cx = 0
    for idx, child in enumerate(ol["groups"]):
        newNodes = draw_groups_recursive(d, child, x + cx, y - GROUPOFFSET)
        for k, node in newNodes.items():
            nodes[k] = node
        cx += child["width"]

    
    cx = (ol["width"]/2) - ((len(ol["nodes"])/2)*ROWSPACING) + (ROUTERSIZE/2)
    for idx, child in enumerate(ol["nodes"]):
        child["x"] = x + cx + (ROUTERSIZE/2)
        child["y"] = y-(LVLSPACING/2)
        d.append(draw.Rectangle(
            child["x"] - (ROUTERSIZE/2), child["y"]-(ROUTERSIZE/2), 
            ROUTERSIZE, 
            ROUTERSIZE, 
            fill="#5167B7", text=child["name"]
        ))
        d.append(draw.Text(child["name"], 12, child["x"], child["y"]-6, fill="white", text_anchor="middle"))
        cx += ROWSPACING
        nodes[child["name"]] = child
    
    return nodes


def calculate_box_size_recursive(level_dict, ol):
    if "neighbours" in ol:
        ol["width"] = ROWSPACING
        return ol

    groupWidths = 0
    
    height = 0
    for idx, child in enumerate(ol["groups"]):
        child = calculate_box_size_recursive(level_dict, child)
        ol["groups"][idx] = child
        groupWidths += child["width"]
        height = max(child["height"]+1, height)

    childrenWidth = 0
    for idx, child in enumerate(ol["nodes"]):
        if child["name"] == "0":
            del ol["nodes"][idx]
            continue
        child = calculate_box_size_recursive(level_dict, child)
        ol["nodes"][idx] = child
        childrenWidth += child["width"]

    ol["nodes"] = sorted(ol["nodes"], key=lambda d: d['name']) 

    # Add padding
    childrenWidth += ROUTERSIZE

    ol["width"] = max(groupWidths, childrenWidth)

    if height == 0:
        height = 1

    ol["height"] = height
    return ol