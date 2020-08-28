'''
M/M/1 Case 1
Run time: 1000s
Source IAT = uniform(30, 60)
Server service time: exponential distribution - 30, 50, 70
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
blocks = 10000
# run_time = 20000

part = [i for i in range(blocks)]

# data DataFrame modeling [0, 1] X ["start_time", "process_time", "process"]]
process_list = ["Process1"]
columns = pd.MultiIndex.from_product([[i for i in range(len(process_list)+1)], ["start_time", "process_time", "process"]])
data = pd.DataFrame([], columns=columns, index=part)

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
Monitor = Monitor(filename)

Source = Source(env, 'Source', data, model, Monitor)

for i in range(len(process_list) + 1):
    if i == len(process_list):
        model['Sink'] = Sink(env, 'Sink', Monitor)
    else:
        model['Process{0}'.format(i + 1)] = Process(env, 'Process{0}'.format(i + 1), server_num, model, Monitor,
                                                    process_time=process_time)

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

# Post-Processing
from PostProcessing_rev import *
print('#' * 80)
print("Post-Processing")
print("M/M/3 Case 1")
print("IAT: uniform(30, 60), Service Time: exponential(30), exponential(50), exponential(70)")

event_tracer = pd.read_csv(filename)
run_time = model['Sink'].last_arrival
# 가동률
print('#' * 80)
# Process
u, idle, working_time = cal_utilization(event_tracer, "Process1", "Process", finish_time=run_time)
print("idle time of Process1: ", idle)
print("total working time of Process1: ", working_time)
print("utilization of Process1: ", u)

# Server
for i in range(server_num):
    u, _, _ = cal_utilization(event_tracer, 'Process1_{0}'.format(i), type="SubProcess", finish_time=run_time)
    print("utilization of Server {0}: ".format(i), u)

# Lead Time
print("average lead time: ", cal_leadtime(event_tracer, finish_time=run_time))

# WIP
print("WIP of entire model: ", np.mean(wip(event_tracer, WIP_type="WIP_m")))

