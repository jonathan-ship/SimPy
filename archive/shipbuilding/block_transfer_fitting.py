import simpy
import time
import os
import scipy.stats as st
import numpy as np
import pandas as pd

from SimComponents import Sink, Process, Source, Monitor, Part

# 코드 실행 시작 시각
start_0 = time.time()

# DATA PRE-PROCESSING
blocks = 18000  # 블록 수
blocks_1 = blocks + 1000  # 1000 = 음수 처리를 위한 여유분
df_part = pd.DataFrame([i for i in range(blocks)], columns=["part"])

columns = pd.MultiIndex.from_product([[i for i in range(4)], ['start_time', 'process_time', 'process']])
data = pd.DataFrame([], columns=columns)

# process 1 : Assembly
data[(0, 'start_time')] = np.floor(st.chi2.rvs(df=1.53, loc=-0, scale=0.22, size=blocks))
data[(0, 'start_time')] = data[(0, 'start_time')].cumsum()
temp = np.round(st.exponnorm.rvs(K=7.71, loc=2.40, scale=1.70, size=blocks_1))
data[(0, 'process_time')] = temp[temp > 0][:blocks]
data[(0, 'process')] = 'Assembly'

# process 2 : Outfitting
data[(1, 'start_time')] = 0
temp_2 = np.round(st.chi2.rvs(df=1.63, loc=1.00, scale=7.43, size=blocks_1))
data[(1, 'process_time')] = temp_2[temp_2 > 0][:blocks]
data[(1, 'process')] = 'Outfitting'

# process 3 : Painting
data[(2, 'start_time')] = 0
temp_3 = np.round(st.exponnorm.rvs(K=1.75, loc=8.53, scale=2.63, size=blocks_1))
data[(2, 'process_time')] = temp_3[temp_3 > 0][:blocks]
data[(2, 'process')] = 'Painting'

# Sink
data[(3, 'start_time')] = None
data[(3, 'process_time')] = None
data[(3, 'process')] = 'Sink'

data = pd.concat([df_part, data], axis=1)
process_list = ['Assembly', 'Outfitting', 'Painting']

parts = []
for i in range(len(data)):
    parts.append(Part(data.index[i], data.iloc[i]))

# Modeling
env = simpy.Environment()

##
model = {}

# 작업장 수
m_assy = 2
m_oft = 2
m_pnt = 2
server_num = [m_assy, m_oft, m_pnt]
filepath = '../result/event_log_block_movement_fitting.csv'
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

# for process in process_list:
#     print("server: ", np.max(model[process].len_of_server))

print('#' * 80)
print("Results of Block Transfer(fitting) simulation")
print('#' * 80)

# 코드 실행 시간
print("data pre-processing : ", start - start_0)
print("simulation execution time :", finish - start)
print("total time : ", finish - start_0)

# DATA POST-PROCESSING
# Event Tracer을 이용한 후처리
from PostProcessing import *
print('#' * 80)
print("Data Post-Processing")
print('#' * 80)

event_tracer = Monitor.save_event_tracer()
# # 가동률
# print('#' * 80)
# for i in range(len(process_list)):
#     process = process_list[i]
#     u, idle, working_time = cal_utilization(event_tracer, process, "Process", finish_time=model['Sink'].last_arrival)
#     print("utilization of {0} : ".format(process), u)
#     print("idle time of {0} : ".format(process), idle)
#     print("total working time of {0} : ".format(process), working_time)
#     print("#"*80)
#
# print("total lead time: ", model['Sink'].last_arrival)