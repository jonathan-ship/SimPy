import simpy
import time
import scipy.stats as st
import pandas as pd
import numpy as np

from SimComponents import Sink, Process, Source, Monitor

# 코드 실행 시작 시각
start_0 = time.time()

# DATA PRE-PROCESSING
blocks = 1000  # 블록 수
df_part = pd.DataFrame([i for i in range(blocks)], columns=["part"])

process_list = ['process1', 'process2']
columns = pd.MultiIndex.from_product([[i for i in range(len(process_list)+1)], ['start_time', 'process_time', 'process']])
data = pd.DataFrame([], columns=columns)

# process 1
data[(0, 'start_time')] = st.expon.rvs(loc=25, scale=1, size=blocks)
data[(0, 'start_time')] = data[(0, 'start_time')].cumsum()
data[(0, 'process_time')] = st.gamma.rvs(a=0.16, loc=0, scale=137.5, size=blocks)
data[(0, 'process')] = 'process1'

# process 2
data[(1, 'start_time')] = 0
data[(1, 'process_time')] = st.gamma.rvs(a=1, loc=0, scale=23, size=blocks)
data[(1, 'process')] = 'process2'

# Sink
data[(2, 'start_time')] = None
data[(2, 'process_time')] = None
data[(2, 'process')] = 'Sink'

data = pd.concat([df_part, data], axis=1)

##
env = simpy.Environment()
model = {}

# 작업장 수
m_assy = 2
m_oft = 2
m_pnt = 2
server_num = [m_assy, m_oft, m_pnt]
filepath = '../result/event_log_factory_physics.csv'
Monitor = Monitor(filepath)

# Source
Source = Source(env, 'Source', data, model, Monitor)

# Process Modeling
for i in range(len(process_list) + 1):
    if i == len(process_list):
        model['Sink'] = Sink(env, 'Sink', Monitor)
    else:
        model[process_list[i]] = Process(env, process_list[i], server_num[i], model, Monitor)

# Run it
start = time.time()  # 시뮬레이션 시작 시각
env.run()
finish = time.time()  # 시뮬레이션 종료 시각

for process in process_list:
    print("server: ", np.max(model[process].len_of_server))

print('#' * 80)
print("Results of Factory Physics Simulation")
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

