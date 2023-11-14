'''
D/D/1 Case 1
# Run time: 1000s
Source IAT = 10
Server service time: 10s
'''
import simpy
import pandas as pd
import time

from SimComponents import Source, Sink, Process, Monitor, Part

start_run = time.time()

server_num = 1
blocks = 1000
run_time = 1000

# df_part: part_id
part = [i for i in range(blocks)]

# data DataFrame modeling [0, 1] X ["start_time", "process_time", "process"]]
process_list = ["Process1"]

# # Process1
# data[(0, 'start_time')] = [10*i for i in range(blocks)]
# data[(0, 'process_time')] = [10 for i in range(blocks)]
# data[(0, 'process')] = "Process1"
#
# # Sink
# data[(1, 'start_time')] = None
# data[(1, 'process_time')] = None
# data[(1, 'process')] = 'Sink'

# Part class
parts = list()
for i in range(blocks):
    parts.append(Part(i, {'start_time':[10*i, None], 'process_time': [10, None], 'process': ['Process1', 'Sink']}))


# Simulation Modeling
env = simpy.Environment()
process_dict = {}  # process_dict

# Monitor
filepath = '../result/event_log_DD1_1.csv'
monitor = Monitor(filepath)

# Source class
source = Source(env, parts, process_dict, Monitor)

process_dict['Sink'] = Sink(env, monitor)

# Process class
for i in range(len(process_list)):
    process_dict['Process{0}'.format(i + 1)] = Process(env, 'Process{0}'.format(i + 1), server_num, process_dict, monitor)

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

# # Post-Processing
# from PostProcessing import *
# print('#' * 80)
# print("Post-Processing")
# print("D/D/1 Case 1")
# print("IAT: 10s, Service Time: 10s")
#
# event_tracer = Monitor.save_event_tracer()
#
# # 가동률
# print('#' * 80)
# u, idle, working_time = cal_utilization(event_tracer, "Process1", "Process", finish_time=run_time)
#
# print("idle time of Process1: ", idle)
# print("total working time of Process1: ", working_time)
# print("utilization of Process1: ", u)
#
# # Lead Time
# print("average lead time: ", cal_leadtime(event_tracer, finish_time=run_time))
#
# # WIP
# print("WIP of entire model: ", np.mean(cal_wip(event_tracer)))