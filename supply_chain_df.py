import os
import simpy
import time
import pandas as pd
import scipy.stats as st

from SimComponents import Source, Sink, Process
from Postprocessing import Utilization, Queue

# 코드 실행 시작 시각
start_0 = time.time()

# DATA INPUT
data_all = pd.read_excel('./data/spool_data_for_simulation.xlsx')
data_all = data_all[['NO_SPOOL', '제작협력사', '도장협력사', "Plan_makingLT", "Actual_makingLT", "Predicted_makingLT",
                 "Plan_paintingLT", "Actual_paintingLT", "Predicted_paintingLT"]]

data = data_all.rename(columns={'제작협력사': 'process1', '도장협력사': 'process2', 'NO_SPOOL': 'part'}, inplace=False)
data['process1'] = data['process1'] + '_1'
data['process2'] = data['process2'] + '_2'

# DATA PRE-PROCESSING
# part 정보
df_part = pd.DataFrame(data["part"])

# 작업 정보
columns = pd.MultiIndex.from_product([[0, 1, 2], ['start_time', 'process_time', 'process']])
df = pd.DataFrame([], columns=columns)

# start_time
# IAT
IAT = st.expon.rvs(loc=28, scale=1, size=len(data))  # 첫 번째 공정의 작업시간의 평균 = 27.9
start_time = IAT.cumsum()
df[(0, 'start_time')] = start_time
df[(1, 'start_time')] = 0
df[(2, 'start_time')] = None

# process_time - Plan, Actual, Predicted 중 선택
df[(0, 'process_time')] = data['Actual_makingLT']
df[(1, 'process_time')] = data['Actual_paintingLT']
df[(2, 'process_time')] = None

# process
df[(0, 'process')] = data['process1']
df[(1, 'process')] = data['process2']
df[(2, 'process')] = 'Sink'

# part 정보와 process 정보의 dataframe 통합(열 기준)
df = pd.concat([df_part, df], axis=1)

# Modeling
env = simpy.Environment()

##
event_tracer = {"event": [], "time": [], "part": [], "process": []}
process_list = list(data.drop_duplicates(['process1'])['process1'])
process_list += list(data.drop_duplicates(['process2'])['process2'])
process_dict = {}
process = []
m_dict = {}

# Source, Sink modeling
Source = Source(env, 'Source', df, process_dict, len(df), event_tracer=event_tracer, data_type="df")
Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)

# Process modeling
for i in range(len(process_list)):
    m_dict[process_list[i]] = 1
    process.append(Process(env, process_list[i], m_dict[process_list[i]], process_dict, event_tracer=event_tracer, qlimit=10000))
for i in range(len(process_list)):
    process_dict[process_list[i]] = process[i]
process_dict['Sink'] = Sink

# Simulation
start = time.time()  # 시뮬레이션 실행 시작 시각
env.run()
finish = time.time()  # 시뮬레이션 실행 종료 시각

print('#' * 80)
print("Results of simulation")
print('#' * 80)

# 코드 실행 시간
print("data pre-processing : ", start - start_0)
print("total time : ", finish - start_0)
print("simulation execution time :", finish - start)

# 총 리드타임 - 마지막 part가 Sink에 도달하는 시간
print("Total Lead Time :", Sink.last_arrival, "\n")

# save data
save_path = './result'
if not os.path.exists(save_path):
    os.makedirs(save_path)

# event tracer dataframe으로 변환
df_event_tracer = pd.DataFrame(event_tracer)
df_event_tracer.to_excel(save_path + '/event_supply_chain.xlsx')

# DATA POST-PROCESSING
# Event Tracer을 이용한 후처리
print('#' * 80)
print("Data Post-Processing")
print('#' * 80)

# 가동률
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