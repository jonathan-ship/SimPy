import simpy
import time
import os
import pandas as pd
import numpy as np

from SimComponents import Source, Sink, Process
from Postprocessing import Utilization, ArrivalRateAndThroughput, Queue

# 코드 실행 시작 시각
start_0 = time.time()

# DATA PRE-PROCESSING
data_all = pd.read_csv('./data/block_transfer.csv', dtype={'PROJ_NO': object})

df_part = pd.DataFrame(data_all["PROJ_NO"], columns=["part"])

data = pd.DataFrame()
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
Source = Source(env, 'Source', df, process_dict, len(data), event_tracer=event_tracer, data_type="df")
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

# Arrival rate, Throughput
ArrivalRateAndThroughput = ArrivalRateAndThroughput(df_event_tracer, process_list)
ArrivalRateAndThroughput.arrival_rate()
ArrivalRateAndThroughput.throughput()
arrival_rate = ArrivalRateAndThroughput.process_arrival_rate
throughput = ArrivalRateAndThroughput.process_throughput

print('#' * 80)
print("Arrival rate : ", arrival_rate)
print("Throughput : ", throughput)

# process 별 평균 대기시간, 총 대기시간
Queue = Queue(df_event_tracer, process_list)
Queue.waiting_time()
print('#' * 80)
for process in process_list:
    print("average waiting time of {} : ".format(process), Queue.average_waiting_time_dict[process])
for process in process_list:
    print("total waiting time of {} : ".format(process), Queue.total_waiting_time_dict[process])

# throughput and arrival_rate
# if Throughput_graph:
#     smoothing = 1000
#     throughput_assy = pd.Series(Monitor1.throughput).rolling(window=smoothing, min_periods=1).mean()
#     throughput_oft = pd.Series(Monitor2.throughput).rolling(window=smoothing, min_periods=1).mean()
#     throughput_pnt = pd.Series(Monitor3.throughput).rolling(window=smoothing, min_periods=1).mean()
#     arrival_rate_assy = pd.Series(Monitor1.arrival_rate).rolling(window=smoothing, min_periods=1).mean()
#     arrival_rate_oft = pd.Series(Monitor2.arrival_rate).rolling(window=smoothing, min_periods=1).mean()
#     arrival_rate_pnt = pd.Series(Monitor3.arrival_rate).rolling(window=smoothing, min_periods=1).mean()
#
#     fig, ax = plt.subplots(3, 1, squeeze=False)
#
#     ax[0][0].plot(Monitor1.time, arrival_rate_assy, label='arrival_rate')
#     ax[0][0].plot(Monitor1.time, throughput_assy, label='throughput')
#     ax[1][0].plot(Monitor2.time, arrival_rate_oft, label='arrival_rate')
#     ax[1][0].plot(Monitor2.time, throughput_oft, label='throughput')
#     ax[2][0].plot(Monitor3.time, arrival_rate_pnt, label='arrival_rate')
#     ax[2][0].plot(Monitor3.time, throughput_pnt, label='throughput')
#
#     ax[0][0].set_xlabel('time[day]')
#     ax[0][0].set_ylabel('rate[EA/day]')
#     ax[1][0].set_xlabel('time[day]')
#     ax[1][0].set_ylabel('rate[EA/day]')
#     ax[2][0].set_xlabel('time[day]')
#     ax[2][0].set_ylabel('rate[EA/day]')
#
#     ax[0][0].set_title("Arrival_rate/Throughput - {0}".format(Monitor1.port.name))
#     ax[1][0].set_title("Arrival_rate/Throughput - {0}".format(Monitor2.port.name))
#     ax[2][0].set_title("Arrival_rate/Throughput - {0}".format(Monitor3.port.name))
#
#     plt.legend()
#     plt.tight_layout()
#     plt.show()
#
#     if save_graph:
#         fig.savefig(save_path + '/ArrivalRate_Throughput.png')
#
# # WIP and m
# if WIP_graph:
#     fig, ax = plt.subplots(3, 1, squeeze=False)
#
#     ax[0][0].plot(Monitor1.time, Monitor1.WIP, label='WIP')
#     ax[0][0].plot(Monitor1.time, Monitor1.M, label='m')
#     ax[1][0].plot(Monitor2.time, Monitor2.WIP, label='WIP')
#     ax[1][0].plot(Monitor2.time, Monitor2.M, label='m')
#     ax[2][0].plot(Monitor3.time, Monitor3.WIP, label='WIP')
#     ax[2][0].plot(Monitor3.time, Monitor3.M, label='m')
#
#     ax[0][0].set_xlabel('time[day]')
#     ax[0][0].set_ylabel('num')
#     ax[1][0].set_xlabel('time[day]')
#     ax[1][0].set_ylabel('num')
#     ax[2][0].set_xlabel('time[day]')
#     ax[2][0].set_ylabel('num')
#
#     ax[0][0].set_title("WIP/m - {0}".format(Monitor1.port.name))
#     ax[1][0].set_title("WIP/m - {0}".format(Monitor2.port.name))
#     ax[2][0].set_title("WIP/m - {0}".format(Monitor3.port.name))
#
#     plt.legend()
#     plt.tight_layout()
#     plt.show()
#
#     if save_graph:
#         fig.savefig(save_path + '/WIP_m.png')