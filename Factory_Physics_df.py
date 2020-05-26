import simpy
import time
import os
import scipy.stats as st
import pandas as pd

from SimComponents import Sink, Process, Source
from Postprocessing import Utilization, Queue

# 코드 실행 시작 시각
start_0 = time.time()

# DATA PRE-PROCESSING
blocks = 18000  # 블록 수
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

# Modeling
env = simpy.Environment()

##
event_tracer = {"event": [], "time": [], "part": [], "process": []}
process_dict = {}
process = []

# 기계 수
m_1 = 1
m_2 = 1
m_dict = {'process1': m_1, 'process2': m_2}

# Source, Sink modeling
Source = Source(env, 'Source', data, process_dict, blocks, event_tracer=event_tracer, data_type="df")
Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)

# Process modeling
for i in range(len(process_list)):
    process.append(Process(env, process_list[i], m_dict[process_list[i]], process_dict, event_tracer=event_tracer, qlimit=10000))
for i in range(len(process_list)):
    process_dict[process_list[i]] = process[i]
process_dict['Sink'] = Sink

# Run it
start = time.time()
env.run()
finish = time.time()

print('#' * 80)
print("Results of simulation")
print('#' * 80)

# 코드 실행 시간
print("data pre-processing : ", start - start_0)  # 시뮬레이션 시작 시각
print("total time : ", finish - start_0)
print("simulation execution time :", finish - start)  # 시뮬레이션 종료 시각

# 총 리드타임 - 마지막 part가 Sink에 도달하는 시간
print("Total Lead Time :", Sink.last_arrival)

# save data
save_path = './result'
if not os.path.exists(save_path):
    os.makedirs(save_path)

# event tracer dataframe으로 변환
df_event_tracer = pd.DataFrame(event_tracer)
df_event_tracer.to_excel(save_path + '/event_Factory_Physics.xlsx')

# DATA POST-PROCESSING
# Event Tracer을 이용한 후처리
print('#' * 80)
print("Data Post-Processing")
print('#' * 80)

# 가동율
Utilization = Utilization(df_event_tracer, process_dict, process_list)
Utilization.utilization()
utilization = Utilization.u_dict

for process in process_list:
    print("utilization of {} : ".format(process), utilization[process])

# process 별 평균 대기시간, 총 대기시간
Queue = Queue(df_event_tracer, process_list)
Queue.waiting_time()
print('#' * 80)
for process in process_list:
    print("average waiting time of {} : ".format(process), Queue.average_waiting_time_dict[process])
for process in process_list:
    print("total waiting time of {} : ".format(process), Queue.total_waiting_time_dict[process])