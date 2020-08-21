'''
M/M/1 Case 1
Run time: 1000s
Source IAT = uniform(30, 60)
Server service time: exponential distribution - 30, 50, 70
??: Sink delay time
'''
import simpy
import pandas as pd
import numpy as np
import scipy.stats as st
import functools
import random
import time
import os

from SimComponents_rev import Source, Sink, Process, Monitor

start_run = time.time()

server_num = 3
blocks = 1000

# df_part: part_id
df_part = pd.DataFrame([i for i in range(blocks)], columns=["part"])

# data DataFrame modeling [0, 1] X ["start_time", "process_time", "process"]]
process_list = ["Process1"]
columns = pd.MultiIndex.from_product([[i for i in range(len(process_list)+1)], ["start_time", "process_time", "process"]])
data = pd.DataFrame([], columns=columns)

# IAT
IAT = st.uniform.rvs(30, 30, size=blocks)
start_time = IAT.cumsum()

# Process1
data[(0, 'start_time')] = start_time
data[(0, 'process_time')] = None
data[(0, 'process')] = "Process1"

# Sink
data[(1, 'start_time')] = None
data[(1, 'process_time')] = None
data[(1, 'process')] = 'Sink'

data = pd.concat([df_part, data], axis=1)

# process_time
service_time_1 = functools.partial(np.random.exponential, 50)
service_time_2 = functools.partial(np.random.exponential, 30)
service_time_3 = functools.partial(np.random.exponential, 70)

# Simulation Modeling
env = simpy.Environment()
model = {}  # process_dict
process_time = {"Process1": [service_time_1, service_time_2, service_time_3]}  # server에 할당할 process time

# Monitoring
filename = './result/event_log_MM3.csv'
Monitor = Monitor(filename, blocks)

Source = Source(env, 'Source', data, model, Monitor)

for i in range(len(process_list) + 1):
    if i == len(process_list):
        model['Sink'] = Sink(env, 'Sink', Monitor)
    else:
        model['Process{0}'.format(i + 1)] = Process(env, 'Process{0}'.format(i + 1), server_num, model, Monitor,
                                                    process_time=process_time, routing_logic="most_unutilized")

start_sim = time.time()
env.run(until=20000)
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
print('#' * 80)
print("Post-Processing")
print("M/M/3 Case 1")
print("IAT: uniform(30, 60), Service Time: exponential(30), exponential(50), exponential(70)")

event_tracer = pd.read_csv(filename)
# 가동률
print('#' * 80)
# Process
utilization_process = Utilization(event_tracer, model, "Process1", model['Sink'].last_arrival)
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

