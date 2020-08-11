'''
D/D/3 Case 1
Run time: 1000s
Source IAT = 10
Server service time: 각 10초씩
'''
import simpy
import pandas as pd
import numpy as np
import time
import os

from SimComponents_rev import Source, Sink, Process

start_run = time.time()

server_num = 3
blocks = 100 # Run_time / IAT

# df_part: part_id
df_part = pd.DataFrame([i for i in range(blocks)], columns=["part"])

# data DataFrame modeling
process_list = ["Process1"]
columns = pd.MultiIndex.from_product([[i for i in range(len(process_list)+1)], ["start_time", "process_time", "process"]])
data = pd.DataFrame([], columns=columns)

# Process1
data[(0, 'start_time')] = [10*i for i in range(blocks)]
data[(0, 'process_time')] = None
data[(0, 'process')] = "Process1"

# Sink
data[(1, 'start_time')] = None
data[(1, 'process_time')] = None
data[(1, 'process')] = 'Sink'

data = pd.concat([df_part, data], axis=1)

# Simulation Modeling
env = simpy.Environment()
model = {}
process_time = {"Process1": [10.0, 10.0, 10.0]}
event_tracer = pd.DataFrame(columns=["TIME", "EVENT", "PART", "PROCESS"])

Source = Source(env, 'Source', data, model, event_tracer)

for i in range(len(process_list) + 1):
    if i == len(process_list):
        model['Sink'] = Sink(env, 'Sink', event_tracer)
    else:
        model['Process{0}'.format(i+1)] = Process(env, 'Process{0}'.format(i+1), server_num, model, event_tracer, process_time=process_time, routing_logic="most_unutilized")

start_sim = time.time()
env.run()
finish_sim = time.time()

print('#' * 80)
print("Results of simulation")
print('#' * 80)

# 코드 실행 시간
print("data pre-processing : ", start_sim - start_run)  # 시뮬레이션 시작 시각
print("total time : ", finish_sim - start_run)
print("simulation execution time :", finish_sim - start_sim)  # 시뮬레이션 종료 시각


# save data
save_path = './result'
if not os.path.exists(save_path):
    os.makedirs(save_path)

event_tracer.to_excel(save_path +'/DD3_case1.xlsx')

# Post-Processing
from PostProcessing_rev import Utilization, LeadTime
utilization_process = Utilization(event_tracer, model, "Process1")
print('#' * 80)
print("Post-Processing")
print("D/D/3 Case 1")
print("IAT: 10s, Service Time: 10s, 10s, 10s")

# 가동률
print('#' * 80)
print("utilization of Process1: ", utilization_process.utilization())
for i in range(server_num):
    utilization_server = Utilization(event_tracer, model, model["Process1"].server[i].name)
    print("utilization of server {0}: ".format(i), utilization_server.utilization())

# Avg.Lead time
print('#' * 80)
leadtime = LeadTime(event_tracer)
print("Average Lead time: ", leadtime.avg_LT())