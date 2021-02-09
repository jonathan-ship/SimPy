import networkx as nx
import pandas as pd
import numpy as np
# import graphviz
# import pydot

proc_data = pd.read_csv('../network/master_plan_전처리.csv', encoding='utf-8')
proc_data = proc_data.fillna('NaN')
print(proc_data)

proc_data = proc_data.iloc[1:]
proc_data.index = list(proc_data.iloc[:, 0])
print(proc_data)


process_dict = dict()
process_list = list()
location_type_dict = dict()

######### Road Fequency data 필요(Transporter가 어떤 도로를 많이 썼는지 굵은 줄로 표시)


# Calculating shortest 'location_type_from' -> 'location_type_to' distance
# proc_network 에서 이 함수를 호출하여 gis 상의 최단거리 계산
def get_shortest_path_distance(graph, location_type_from, location_type_to):
    shortest_path_length_dict = dict(nx.shortest_path_length(graph, weight='distance'))
    shortest_path_length = shortest_path_length_dict[location_type_from][location_type_to]

    return shortest_path_length


for idx, row in proc_data.iterrows():
    proc_list = list()
    for i, item in zip(range(len(list(row))), row):
        if i != 0 and i % 3 == 0 and item != 'NaN':
            proc_list.append(item)
    process_dict[idx] = proc_list


for key, values in process_dict.items():
    for value in values:
        if value not in process_list:
            process_list.append(value)


# gis network : 각 작업장 간의 gis 상의 연결관계 및 거리 정보에 대한 network 생성
# gis_network의 node 명칭 : location_type(작업장 이름)
# gis_network의 edge attribute : 'distance' -> 두 작업장 사이의 거리
gis_network = nx.Graph()

location_types = ['작업장_{0}'.format(i + 1) for i in range(len(process_list))]
#print(location_types)
for i, location_type in enumerate(location_types):
    if i < len(location_types) - 1:
        gis_network.add_edges_from([(location_types[i], location_types[i + 1], {'distance': np.random.randint(0, 20)})])

print(gis_network.adj)
print(dict(nx.shortest_path_length(gis_network, weight= 'distance')))



# proc_network : 각 공정정보 및 공정 간 연결관계를 나타내는 network 생성
# proc_network의 node 명칭 : 각 Process 명
# proc_network의 node attribute : 'location_type'
# proc_network의 edge attribute : 'shortest_distance', 'relation_type'
proc_network = nx.DiGraph()
# add nodes of proc_network
for i, node in enumerate(process_list):
    proc_network.add_nodes_from([(node, {'location_type': '작업장_{0}'.format(i + 1)})])

print(proc_network.nodes)

for key, values in process_dict.items():
    for i, value in enumerate(values):
        if i < len(values) - 1:
            proc_network.add_edge(values[i], values[i + 1])
            proc_network.edges[values[i], values[i + 1]]['shortest_distance'] = get_shortest_path_distance(gis_network, proc_network.nodes[values[i]]['location_type'],
                                                                                           proc_network.nodes[values[i + 1]]['location_type'])
            proc_network.edges[values[i], values[i + 1]]['relation_type'] = 'FS'

print(proc_network.adj)
print(proc_network.nodes['HF010'])





