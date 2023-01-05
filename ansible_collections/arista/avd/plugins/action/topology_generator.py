from __future__ import absolute_import, division, print_function

__metaclass__ = type


import glob

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase

import ansible_collections.arista.avd.plugins.plugin_utils.topology_generator_utils as gt


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = {}
        result = super().run(tmp, task_vars)
        del tmp  # tmp no longer has any effect
        if self._task.args and "structured_config" not in self._task.args:
            raise AnsibleActionFail("Missing 'structured_config' variable.")
        path = self._task.args["structured_config"]

        # fabric_name logic need to check 
        # fabric_name = task_vars["fabric_name"]
        # inventory_group = task_vars["groups"][fabric_name]
        # print("inventory_group")
        # print(inventory_group)
        # self.driver_func(path, inventory_group)


        # fabric_name = task_vars["hostvars"]["fabric_name"]
        # inventory_group = task_vars["groups"][fabric_name]
        # raise Exception(inventory_group)
        # print(task_vars)
        # exit()
        # print(inventory_group)

        # old logic
        inventory_group = ['SPINE1', 'SPINE2', 'LEAF1', 'LEAF2', 'LEAF3', 'LEAF4']
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

        # print(node_dict)
        # exit()

        global_node_list, graph_dict = gt.create_graph_dict(output_list, inventory_group)

        level_dict, node_level_dict = gt.find_node_levels(graph_dict, "0", global_node_list)

        print(graph_dict)

        rank_nodes_list = []
        for v in level_dict.values():
            rank_nodes_list += v

        undefined_rank_nodes = list(set(rank_nodes_list) ^ set(global_node_list))

        # node_port_val = {top, bottom, left, right}
        node_port_val = {}

        print("1")
        # print("========")
        # top and bottom port values
        # print("node_level_dict")
        # example 'FIREWALL': 1, 'SPINE1': 2, 'SPINE2': 2, 'LEAF1': 3

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
        print("2")
        for node_val, node_details in graph_dict.items():
            if node_val not in undefined_rank_nodes:

                for i in node_details:
                    node_neighbor_str = None

                    node_neighbor_str = [node_val] + [i["nodePort"]] + [i["neighborDevice"]] + [i["neighborPort"]]
                    # print(node_neighbor_str)
                    # print("===")
                    node_neighbor_str.sort()
                    node_neighbor_str = "_".join(node_neighbor_str)
                    # print(node_neighbor_str)
                    if node_neighbor_str not in check_same_node:
                        check_same_node.append(node_neighbor_str)
                        if node_val not in temp_graph_dict.keys():
                            temp_graph_dict[node_val] = [i]
                        else:
                            temp_graph_dict[node_val] = temp_graph_dict[node_val] + [i]
                    #'SPINE1': [{'nodePort': '1', 'neighborDevice': 'LEAF1', 'neighborPort': '1'}]
                    #'FIREWALL': 1, 'SPINE1': 2, 'SPINE2': 2, 'LEAF1': 3

                    #node_level_dict
                    #{'0': 0, 'SPINE2': 1, 'SPINE1': 1, 'LEAF1': 1, 'LEAF2': 1, 'LEAF3': 1, 'LEAF4': 1}
                    # print("node_level_dict")
                    # print(node_level_dict)
                    # print("\n\n")
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
        # left right ports
        # print("level_dict")
        # #example 1: ['FIREWALL'], 2: ['SPINE1', 'SPINE2'], 3: ['LEAF1', 'LEAF2', 'LEAF3', 'LEAF4'],
        # print(level_dict)
        # #{0: ['0'], 1: ['SPINE2', 'SPINE1', 'LEAF1', 'LEAF2', 'LEAF3', 'LEAF4']}
        # print("\n\n")
        # print(graph_dict)
        # #{'SPINE2': [{'nodePort': '1', 'neighborDevice': 'LEAF1', 'neighborPort': '2'}]
        # print("\n\n")
        # print(node_port_val)
        # print("\n\n")

        #  V1 logic for left right node ports
        # for level_list in level_dict.values():
        #     # print("===============")
        #     # print(level_list)
        #     # # level_list.sort()
        #     # print("===============")
        #     # print(level_list)
        #     if len(level_list) > 1: 
        #         for i in range(len(level_list)-1):
        #             # print("\n")
        #             # print(f"{level_list[i]}  {level_list[i+1]}") 
        #             # print(f"{graph_dict[level_list[i]]}") 
        #             # print(f"{graph_dict[level_list[i + 1]]}")
        #             for node_detail in graph_dict[level_list[i]]:
        #                 if node_detail["neighborDevice"] == level_list[i + 1]:
        #                     #left node => right port    
        #                     if (node_detail["nodePort"] not in node_port_val[level_list[i]]["right"]) and (node_detail["nodePort"] not in node_port_val[level_list[i]]["checked"]):
        #                         node_port_val[level_list[i]]["right"] = node_port_val[level_list[i]]["right"] + [node_detail["nodePort"]]
        #                         node_port_val[level_list[i]]["checked"] = node_port_val[level_list[i]]["checked"] + [node_detail["nodePort"]]
                            
        #                     #right node => left port 
        #                     if (node_detail["neighborPort"] not in node_port_val[level_list[i + 1]]["left"]) and (node_detail["neighborPort"] not in node_port_val[level_list[i + 1]]["checked"]):
        #                         node_port_val[level_list[i + 1]]["left"] = node_port_val[level_list[i + 1]]["left"] + [node_detail["neighborPort"]]
        #                         node_port_val[level_list[i + 1]]["checked"] = node_port_val[level_list[i + 1]]["checked"] + [node_detail["neighborPort"]]

        print("3")
        for level_list in level_dict.values():
            # level_list.sort()
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


        for k, v in node_port_val.items():
            print(f"{k} {v}") 
        print("4")
        graph_dict = temp_graph_dict
        # print(graph_dict)




        gt.generate_topology(level_dict, graph_dict, output_list, undefined_rank_nodes, node_port_val)
