from __future__ import absolute_import, division, print_function

__metaclass__ = type


import glob
import os

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase

import ansible_collections.arista.avd.plugins.plugin_utils.topology_generator_utils as gt

import re

_nsre = re.compile('([0-9]+)')
def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(_nsre, s)] 

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = {}
        result = super().run(tmp, task_vars)
        del tmp  # tmp no longer has any effect
        if self._task.args and "structured_config" not in self._task.args:
            raise AnsibleActionFail("Missing 'structured_config' variable.")
        path = self._task.args["structured_config"]

        # fabric_name logic need to check only for molecule
        # fabric_name = task_vars["fabric_name"]
        # inventory_group = task_vars["groups"][fabric_name]
        # print("inventory_group")
        # print(inventory_group)
        # self.driver_func(path, inventory_group)


        # old logic
        inventory_group = [i.split(".")[0] for i in os.listdir(path)]
        # inventory_group = ['DC1-POD1-LEAF1A', 'DC2-SUPER-SPINE1', 'DC2-SUPER-SPINE2', 'DC2-RS1', 'DC2-RS2', 'DC1-SUPER-SPINE1', 'DC1-SUPER-SPINE2', 'DC1-RS1', 'DC1-RS2', 'DC1-POD1-SPINE1', 'DC1-POD1-SPINE2', 'DC1.POD1.LEAF2A', 'DC1-POD1-LEAF2B', 'DC1-POD1-L2LEAF1A', 'DC1-POD1-L2LEAF2A', 'DC1-POD1-L2LEAF2B', 'DC2-POD1-SPINE1', 'DC2-POD1-SPINE2', 'DC2-POD1-LEAF1A', 'DC2-POD1-L2LEAF1A', 'DC2-POD1-LEAF2A', 'DC2-POD1-L2LEAF2A', 'DC1-POD2-SPINE1', 'DC1-POD2-SPINE2', 'DC1-POD2-LEAF1A']
        # inventory_group =  ['SPINE1', 'SPINE2','SUPER-SPINE2','SUPER-SPINE1', 'LEAF1', 'LEAF2', 'LEAF3', 'LEAF4']
        # inventory_group = ['l3-leaf5', 'spine6', 'l2-leaf1', 'l3-leaf6', 'spine7','l2-leaf2','l3-leaf7','spine8','l2-leaf3','l3-leaf8','spine9','l2-leaf4','l3-leaf9','super-spine1','l3-leaf1','spine1'  ,'super-spine2','l3-leaf10','spine2'  ,'super-spine3','l3-leaf2','spine3'  ,'super-spine4','l3-leaf3','spine4','l3-leaf4','spine5']
        self.driver_func(path, inventory_group)
        return result

    # def driver_func(self, directory_path):
    def driver_func(self, directory_path, inventory_group):  
        files = glob.glob(directory_path + "/*.yml")

        output_list = []
        for file in files:
            data = gt.read_yaml_file(file)
            node_dict = gt.create_node_dict(data, file)
            output_list = gt.structured_config_to_topology_input(output_list, node_dict, data["diagram_groups"], current_dict={})

        root_dict = gt.find_root_nodes(output_list[0])
        output_list[0]["nodes"].append(root_dict)


        global_node_list, graph_dict = gt.create_graph_dict(output_list, inventory_group)

        print(graph_dict)
        level_dict, node_level_dict = gt.find_node_levels(graph_dict, "0", global_node_list)

        rank_nodes_list = []
        for v in level_dict.values():
            rank_nodes_list += v

        undefined_rank_nodes = list(set(rank_nodes_list) ^ set(global_node_list))

        # node_port_val = {top, bottom, left, right}
        node_port_val = {}


        for i in node_level_dict.keys():
            if i not in undefined_rank_nodes:
                node_port_val[i] = {}
                node_port_val[i]["checked"] = []
                node_port_val[i]["top"] = []
                node_port_val[i]["bottom"] = []
                node_port_val[i]["left"] = []
                node_port_val[i]["right"] = []

        # avoid same node neighbour pair
        check_same_node = []
        temp_graph_dict = {}

        for node_val, node_details in graph_dict.items():
            if node_val not in undefined_rank_nodes:

                for i in node_details:
                    node_neighbor_str = None

                    node_neighbor_str = [node_val] + [i["nodePort"]] + [i["neighborDevice"]] + [i["neighborPort"]]

                    node_neighbor_str.sort()
                    node_neighbor_str = "_".join(node_neighbor_str)

                    if node_neighbor_str not in check_same_node:
                        check_same_node.append(node_neighbor_str)
                        if node_val not in temp_graph_dict.keys():
                            temp_graph_dict[node_val] = [i]
                        else:
                            temp_graph_dict[node_val] = temp_graph_dict[node_val] + [i]

                    #node_level_dict
                    # set top and bottom port values
                    if node_level_dict[node_val] < node_level_dict[i["neighborDevice"]]:
                        if i["nodePort"] not in node_port_val[node_val]["bottom"] and i["nodePort"] and i["nodePort"] not in node_port_val[node_val]["checked"]:
                            node_port_val[node_val]["bottom"] = node_port_val[node_val]["bottom"] + [i["nodePort"]]
                            node_port_val[node_val]["checked"] = node_port_val[node_val]["checked"] + [i["nodePort"]]

                        if i["neighborPort"] not in node_port_val[i["neighborDevice"]]["top"] and i["neighborPort"] and i["neighborPort"] not in node_port_val[i["neighborDevice"]]["checked"]:
                            node_port_val[i["neighborDevice"]]["top"] = node_port_val[i["neighborDevice"]]["top"] + [i["neighborPort"]]
                            node_port_val[i["neighborDevice"]]["checked"] = node_port_val[i["neighborDevice"]]["checked"] + [i["neighborPort"]]

                    if node_level_dict[node_val] > node_level_dict[i["neighborDevice"]]:
                        if i["nodePort"] not in node_port_val[node_val]["top"] and i["nodePort"] and i["nodePort"] not in node_port_val[node_val]["checked"]:
                            node_port_val[node_val]["top"] = node_port_val[node_val]["top"] + [i["nodePort"]]
                            node_port_val[node_val]["checked"] = node_port_val[node_val]["checked"] + [i["nodePort"]]

                        if i["neighborPort"] not in node_port_val[i["neighborDevice"]]["bottom"] and i["neighborPort"] and i["neighborPort"] not in node_port_val[i["neighborDevice"]]["checked"]:
                            node_port_val[i["neighborDevice"]]["bottom"] = node_port_val[i["neighborDevice"]]["bottom"] + [i["neighborPort"]]
                            node_port_val[i["neighborDevice"]]["checked"] = node_port_val[i["neighborDevice"]]["checked"] + [i["neighborPort"]]

        for level_pos,level_list in level_dict.items():
            level_list.sort(key=natural_sort_key)

            for i in range(len(level_list) - 1):
                for j in range(i+1,len(level_list)): 
                    for node_detail in graph_dict[level_list[i]]:
                        if node_detail["neighborDevice"] == level_list[j]:
                            #left node => right port    
                            if (node_detail["nodePort"] not in node_port_val[level_list[i]]["right"]) and (node_detail["nodePort"] not in node_port_val[level_list[i]]["checked"]):
                                node_port_val[level_list[i]]["right"] = node_port_val[level_list[i]]["right"] + [node_detail["nodePort"]]
                                node_port_val[level_list[i]]["checked"] = node_port_val[level_list[i]]["checked"] + [node_detail["nodePort"]]
                            
                            #right node => left port 
                            if (node_detail["neighborPort"] not in node_port_val[level_list[j]]["left"]) and (node_detail["neighborPort"] not in node_port_val[level_list[j]]["checked"]):
                                node_port_val[level_list[j]]["left"] = node_port_val[level_list[j]]["left"] + [node_detail["neighborPort"]]
                                node_port_val[level_list[j]]["checked"] = node_port_val[level_list[j]]["checked"] + [node_detail["neighborPort"]]

 
        graph_dict = temp_graph_dict

        gt.generate_topology_hampton(level_dict, graph_dict, output_list, undefined_rank_nodes, node_port_val)
