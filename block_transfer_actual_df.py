import simpy
import time
import os
import pandas as pd

from SimComponents import Source, Sink, Process
from Postprocessing import Utilization, Queue

# 코드 실행 시작 시각
start_0 = time.time()

# DATA INPUT
data_all = pd.read_csv('./data/block_transfer.csv', dtype={'PROJ_NO': object})

# DATA PRE-PROCESSING
data = pd.DataFrame()
data["part"] = data_all["PROJ_NO"] + '_' + data_all['BLK_NO']
data["AAS_CAL"] = pd.to_datetime(data_all["AAS_CAL"], format='%Y-%m-%d')
data["OAS_CAL"] = pd.to_datetime(data_all["OAS_CAL"], format='%Y-%m-%d')
data["PAS_CAL"] = pd.to_datetime(data_all["PAS_CAL"], format='%Y-%m-%d')
data["AA_DATEDIF"] = data_all["AA_DATEDIF"]
data["OA_DATEDIF"] = data_all["OA_DATEDIF"]
data["PA_DATEDIF"] = data_all["PA_DATEDIF"]

data = data[data["AA_DATEDIF"] != 0]
data = data[data["OA_DATEDIF"] != 0]
data = data[data["PA_DATEDIF"] != 0]

data = data[(data["AAS_CAL"].dt.year >= 2015) & (data["AAS_CAL"].dt.year <= 2017)]

initial_date = data["AAS_CAL"].min()

data["AAS_CAL"] = (data["AAS_CAL"] - initial_date).dt.days
data["OAS_CAL"] = (data["OAS_CAL"] - initial_date).dt.days
data["PAS_CAL"] = (data["PAS_CAL"] - initial_date).dt.days

# Assembly 시작 시간 기준으로 정렬
data_1 = data.sort_values(by=["AAS_CAL"], inplace=False)
data = data_1.reset_index(drop=True, inplace=False)

process_list = ['Assembly', 'Outfitting', 'Painting']
start_time_list = ["AAS_CAL", "OAS_CAL", "PAS_CAL"]
process_time_list = ["AA_DATEDIF", "OA_DATEDIF", "PA_DATEDIF"]

# Source에 넣어 줄 dataframe
df_part = data["part"]
columns = pd.MultiIndex.from_product([[i for i in range(4)], ['start_time', 'process_time', 'process']])
df = pd.DataFrame([], columns=columns)

for i in range(len(process_list)):
    df[(i, 'start_time')] = data[start_time_list[i]]
    df[(i, 'process_time')] = data[process_time_list[i]]
    df[(i, 'process')] = process_list[i]

df[(3, 'start_time')], df[(3, 'process_time')], df[(3, 'process')] = None, None, 'Sink'

df = pd.concat([df_part, df], axis=1)

# Modeling
env = simpy.Environment()

##
event_tracer = {"event": [], "time": [], "part": [], "process": []}
process_dict = {}
process = []

# 작업장 수
m_assy = 334
m_oft = 322
m_pnt = 263
m_dict = {'Assembly': m_assy, 'Outfitting': m_oft, 'Painting': m_pnt}

# Source, Sink modeling
Source = Source(env, 'Source', df, process_dict, len(df), event_tracer=event_tracer, data_type="df")
Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)
# Process modeling
for i in range(len(process_list)):
    process.append(Process(env, process_list[i], m_dict[process_list[i]], process_dict, event_tracer=event_tracer, qlimit=10000))
for i in range(len(process_list)):
    process_dict[process_list[i]] = process[i]
process_dict['Sink'] = Sink

# Run it
start = time.time()  # 시뮬레이션 시작 시각
env.run()
finish = time.time()  # 시뮬레이션 종료 시각

print('#' * 80)
print("Results of simulation")
print('#' * 80)

# 코드 실행 시간
print("data pre-processing : ", start - start_0)
print("simulation execution time :", finish - start)
print("total time : ", finish - start_0)

# 총 리드타임 - 마지막 part가 Sink에 도달하는 시간
print("Total Lead Time :", Sink.last_arrival)

# save data
save_path = './result'
if not os.path.exists(save_path):
    os.makedirs(save_path)

# event tracer dataframe으로 변환
df_event_tracer = pd.DataFrame(event_tracer)
df_event_tracer.to_excel(save_path + '/event_block_transfer_actual.xlsx')

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