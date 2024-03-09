'''
D/D/3 Case 2
Run time: 1000s
Source IAT = 10
Server service time: 5,10,15
'''
import simpy
import pandas as pd
import time

from SimComponent.SimComponents import Source, Sink, Process, Monitor, Part

start_run = time.time()

server_num = 3
blocks = 1000
run_time = 1000

part = [i for i in range(blocks)]  # part 이름

# data DataFrame modeling
process_list = ["Process1"]
columns = pd.MultiIndex.from_product([[i for i in range(len(process_list)+1)], ["start_time", "process_time", "process"]])
data = pd.DataFrame([], columns=columns, index=part)

# Process1
data[(0, 'start_time')] = [10*i for i in range(blocks)]
data[(0, 'process_time')] = None
data[(0, 'process')] = "Process1"

# Sink
data[(1, 'start_time')] = None
data[(1, 'process_time')] = None
data[(1, 'process')] = 'Sink'

parts = list()
for i in range(len(data)):
    parts.append(Part(data.index[i], data.iloc[i]))

# Simulation Modeling
env = simpy.Environment()
model = {}
process_time = {"Process1": [5.0, 10.0, 15.0]}

# Monitoring
filepath = '../result/event_log_DD3_1.csv'
Monitor = Monitor(filepath)

Source = Source(env, parts, model, Monitor)

for i in range(len(process_list) + 1):
    if i == len(process_list):
        model['Sink'] = Sink(env, Monitor)
    else:
        model['Process{0}'.format(i + 1)] = Process(env, 'Process{0}'.format(i + 1), server_num, model, Monitor,
                                                    process_time=process_time, routing_logic="least_utilized")

start_sim = time.time()
env.run(until=run_time)
finish_sim = time.time()

print('#' * 80)
print("Results of simulation")
print('#' * 80)

# 코드 실행 시간
print("data pre-processing : ", start_sim - start_run)  # 시뮬레이션 시작 시각
print("total time : ", finish_sim - start_run)
print("simulation execution time :", finish_sim - start_sim)  # 시뮬레이션 종료 시각

# Post-Processing
from PostProcessing import *

event_tracer = Monitor.save_event_tracer()

print('#' * 80)
print("Post-Processing")
print("D/D/3 Case 1")
print("IAT: 10s, Service Time: 10s, 10s, 10s")

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
print("WIP of entire model: ", np.mean(cal_wip(event_tracer)))
