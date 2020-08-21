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

from SimComponents_rev import Source, Sink, Process, Monitor

start_run = time.time()

server_num = 3
blocks = 10000

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

# Monitoring
filename = './result/event_log_DD3_1.csv'
Monitor = Monitor(filename, blocks)

Source = Source(env, 'Source', data, model, Monitor)

for i in range(len(process_list) + 1):
    if i == len(process_list):
        model['Sink'] = Sink(env, 'Sink', Monitor)
    else:
        model['Process{0}'.format(i + 1)] = Process(env, 'Process{0}'.format(i + 1), server_num, model, Monitor,
                                                    process_time=process_time, routing_logic="most_unutilized")

start_sim = time.time()
env.run(until=1000)
finish_sim = time.time()

print('#' * 80)
print("Results of simulation")
print('#' * 80)

# 코드 실행 시간
print("data pre-processing : ", start_sim - start_run)  # 시뮬레이션 시작 시각
print("total time : ", finish_sim - start_run)
print("simulation execution time :", finish_sim - start_sim)  # 시뮬레이션 종료 시각

# Post-Processing
from PostProcessing_rev import Utilization, LeadTime, WIP
event_tracer = pd.read_csv(filename)
utilization_process = Utilization(event_tracer, model, "Process1", model['Sink'].last_arrival)
print('#' * 80)
print("Post-Processing")
print("D/D/3 Case 1")
print("IAT: 10s, Service Time: 10s, 10s, 10s")

# 가동률
print('#' * 80)
# Process
u, idle, working_time = utilization_process.utilization()
print("idle time of Process1: ", idle)
print("total working time of Process1: ", working_time)
print("utilization of Process1: ", u)

# Server
for i in range(server_num):
    utilization_server = Utilization(event_tracer, model, model["Process1"].server[i].name, model['Sink'].last_arrival)
    u, _, _ = utilization_server.utilization()
    print("utilization of Server {0}: ".format(i), u)

# Lead Time
lead_time = LeadTime(event_tracer)
print("average lead time: ", lead_time.avg_LT())

# WIP
wip_m = WIP(event_tracer, WIP_type="WIP_m")
print("WIP of entire model: ", np.mean(wip_m.cal_wip()))
