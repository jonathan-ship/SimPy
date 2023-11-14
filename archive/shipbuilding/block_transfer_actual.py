import simpy
import time
import pandas as pd
import numpy as np

from SimComponents import Source, Sink, Process, Monitor, Part

# 코드 실행 시작 시각
start_0 = time.time()

# DATA INPUT
data_all = pd.read_csv('../data/block_transfer.csv', dtype={'PROJ_NO': object})

# DATA PRE-PROCESSING
data = pd.DataFrame()
data["part"] = data_all["PROJ_NO"] + '_' + data_all['BLK_NO']
data["AAS_CAL"] = pd.to_datetime(data_all["AAS_CAL"], format='%Y-%m-%d')
data["OAS_CAL"] = pd.to_datetime(data_all["OAS_CAL"], format='%Y-%m-%d')
data["PAS_CAL"] = pd.to_datetime(data_all["PAS_CAL"], format='%Y-%m-%d')
data["AA_DATEDIF"] = data_all["AA_DATEDIF"]
data["OA_DATEDIF"] = data_all["OA_DATEDIF"]
data["PA_DATEDIF"] = data_all["PA_DATEDIF"]

data = data[data["AA_DATEDIF"] != 0]
data = data[data["OA_DATEDIF"] != 0]
data = data[data["PA_DATEDIF"] != 0]

data = data[(data["AAS_CAL"].dt.year >= 2015) & (data["AAS_CAL"].dt.year <= 2017)]

initial_date = data["AAS_CAL"].min()

data["AAS_CAL"] = (data["AAS_CAL"] - initial_date).dt.days
data["OAS_CAL"] = (data["OAS_CAL"] - initial_date).dt.days
data["PAS_CAL"] = (data["PAS_CAL"] - initial_date).dt.days

# Assembly 시작 시간 기준으로 정렬
data_1 = data.sort_values(by=["AAS_CAL"], inplace=False)
data = data_1.reset_index(drop=True, inplace=False)

process_list = ['Assembly', 'Outfitting', 'Painting']
start_time_list = ["AAS_CAL", "OAS_CAL", "PAS_CAL"]
process_time_list = ["AA_DATEDIF", "OA_DATEDIF", "PA_DATEDIF"]

# Source에 넣어 줄 dataframe
part = list(data["part"])
columns = pd.MultiIndex.from_product([[i for i in range(len(process_list)+1)], ['start_time', 'process_time', 'process']])
df = pd.DataFrame([], columns=columns, index=part)

for i in range(len(process_list)):
    df[(i, 'start_time')] = list(data[start_time_list[i]])
    df[(i, 'process_time')] = list(data[process_time_list[i]])
    df[(i, 'process')] = process_list[i]

df[(3, 'start_time')], df[(3, 'process_time')], df[(3, 'process')] = None, None, 'Sink'

parts = []
for i in range(len(df)):
    parts.append(Part(df.index[i], df.iloc[i]))

# Modeling
env = simpy.Environment()

##
model = {}

# 작업장 수
m_assy = 2
m_oft = 2
m_pnt = 2
server_num = [m_assy, m_oft, m_pnt]
filepath = '../result/event_log_block_movement_actual.csv'
Monitor = Monitor(filepath)

# Source
Source = Source(env, parts, model, Monitor)

# Process Modeling
for i in range(len(process_list) + 1):
    if i == len(process_list):
        model['Sink'] = Sink(env, Monitor)
    else:
        model[process_list[i]] = Process(env, process_list[i], server_num[i], model, Monitor)

# Run it
start = time.time()  # 시뮬레이션 시작 시각
env.run()
finish = time.time()  # 시뮬레이션 종료 시각


print('#' * 80)
print("Results of Block Transfer(actual) simulation")
print('#' * 80)

# 코드 실행 시간
print("data pre-processing : ", start - start_0)
print("simulation execution time :", finish - start)
print("total time : ", finish - start_0)

event_tracer = Monitor.save_event_tracer()

# DATA POST-PROCESSING
# Event Tracer을 이용한 후처리
from PostProcessing import *
print('#' * 80)
print("Data Post-Processing")
print('#' * 80)

# 가동률
print('#' * 80)
for i in range(len(process_list)):
    process = process_list[i]
    u, idle, working_time = cal_utilization(event_tracer, process, "Process", finish_time=model['Sink'].last_arrival)
    print("utilization of {0} : ".format(process), u)
    print("idle time of {0} : ".format(process), idle)
    print("total working time of {0} : ".format(process), working_time)
    print("#"*80)

print("total lead time: ", model['Sink'].last_arrival)