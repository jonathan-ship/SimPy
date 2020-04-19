import simpy
import random
import functools
import time
import os
from collections import OrderedDict
import pandas as pd
import matplotlib.pyplot as plt
from SimComponents import Source, Sink, Process, Monitor

start_0 = time.time()

# data pre-processing
data_all = pd.read_csv('./data/block_transfer.csv', dtype={'PROJ_NO': object})

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


WIP_graph = False
Throughput_graph = False
save_graph = False

if save_graph:
    save_path = './data/actual_data'
    if not os.path.exists(save_path):
        os.makedirs(save_path)

# samp_dist = functools.partial(random.expovariate, 1) # need to be checked
samp_dist = 1

m_assy = 334
m_oft = 322
m_pnt = 263
m_dict = {'Assembly': m_assy, 'Outfitting': m_oft, 'Painting': m_pnt}


process_dict = {}

# modeling
env = simpy.Environment()
Source = Source(env, 'Source', df, process_dict, len(data), data_type="df")
Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)

process = []
monitor = []
monitor_dict = {}

## Process 할당
for i in range(len(process_list)):
    process.append(Process(env, process_list[i], m_dict[process_list[i]], process_dict, 10000))

for i in range(len(process_list)):
    process_dict[process_list[i]] = process[i]
# Assembly = Process(env, "Assembly", m_assy, qlimit=10000)
# Outfitting = Process(env, "Outfitting", m_oft, qlimit=10000)
# Painting = Process(env, "Painting", m_pnt, qlimit=10000)

process_dict['Sink'] = Sink

Monitor1 = Monitor(env, process_dict['Assembly'], samp_dist)
Monitor2 = Monitor(env, process_dict['Outfitting'], samp_dist)
Monitor3 = Monitor(env, process_dict['Painting'], samp_dist)

# Run it
start = time.time()
env.run()
finish = time.time()

print('#' * 80)
print("Results of simulation")
print('#' * 80)

# 코드 실행 시간
print("total time : ", finish - start_0)
print("simulation execution time :", finish - start)

# 총 리드타임 - 마지막 part가 Sink에 도달하는 시간
print("Total Lead Time :", Sink.last_arrival)


# 가동률
def utilization(activity):
    temp_process = process_dict[activity]
    total_time = (temp_process.process_finish - temp_process.process_start) * temp_process.server_num
    total_working = temp_process.working_time
    u = total_working / total_time
    return u


for process in process_list:
    print('utilization of {} : '.format(process), utilization(process))

# throughput and arrival_rate
if Throughput_graph:
    smoothing = 1000
    throughput_assy = pd.Series(Monitor1.throughput).rolling(window=smoothing, min_periods=1).mean()
    throughput_oft = pd.Series(Monitor2.throughput).rolling(window=smoothing, min_periods=1).mean()
    throughput_pnt = pd.Series(Monitor3.throughput).rolling(window=smoothing, min_periods=1).mean()
    arrival_rate_assy = pd.Series(Monitor1.arrival_rate).rolling(window=smoothing, min_periods=1).mean()
    arrival_rate_oft = pd.Series(Monitor2.arrival_rate).rolling(window=smoothing, min_periods=1).mean()
    arrival_rate_pnt = pd.Series(Monitor3.arrival_rate).rolling(window=smoothing, min_periods=1).mean()

    fig, ax = plt.subplots(3, 1, squeeze=False)

    ax[0][0].plot(Monitor1.time, arrival_rate_assy, label='arrival_rate')
    ax[0][0].plot(Monitor1.time, throughput_assy, label='throughput')
    ax[1][0].plot(Monitor2.time, arrival_rate_oft, label='arrival_rate')
    ax[1][0].plot(Monitor2.time, throughput_oft, label='throughput')
    ax[2][0].plot(Monitor3.time, arrival_rate_pnt, label='arrival_rate')
    ax[2][0].plot(Monitor3.time, throughput_pnt, label='throughput')

    ax[0][0].set_xlabel('time[day]')
    ax[0][0].set_ylabel('rate[EA/day]')
    ax[1][0].set_xlabel('time[day]')
    ax[1][0].set_ylabel('rate[EA/day]')
    ax[2][0].set_xlabel('time[day]')
    ax[2][0].set_ylabel('rate[EA/day]')

    ax[0][0].set_title("Arrival_rate/Throughput - {0}".format(Monitor1.port.name))
    ax[1][0].set_title("Arrival_rate/Throughput - {0}".format(Monitor2.port.name))
    ax[2][0].set_title("Arrival_rate/Throughput - {0}".format(Monitor3.port.name))

    plt.legend()
    plt.tight_layout()
    plt.show()

    if save_graph:
        fig.savefig(save_path + '/ArrivalRate_Throughput.png')

# WIP and m
if WIP_graph:
    fig, ax = plt.subplots(3, 1, squeeze=False)

    ax[0][0].plot(Monitor1.time, Monitor1.WIP, label='WIP')
    ax[0][0].plot(Monitor1.time, Monitor1.M, label='m')
    ax[1][0].plot(Monitor2.time, Monitor2.WIP, label='WIP')
    ax[1][0].plot(Monitor2.time, Monitor2.M, label='m')
    ax[2][0].plot(Monitor3.time, Monitor3.WIP, label='WIP')
    ax[2][0].plot(Monitor3.time, Monitor3.M, label='m')

    ax[0][0].set_xlabel('time[day]')
    ax[0][0].set_ylabel('num')
    ax[1][0].set_xlabel('time[day]')
    ax[1][0].set_ylabel('num')
    ax[2][0].set_xlabel('time[day]')
    ax[2][0].set_ylabel('num')

    ax[0][0].set_title("WIP/m - {0}".format(Monitor1.port.name))
    ax[1][0].set_title("WIP/m - {0}".format(Monitor2.port.name))
    ax[2][0].set_title("WIP/m - {0}".format(Monitor3.port.name))

    plt.legend()
    plt.tight_layout()
    plt.show()

    if save_graph:
        fig.savefig(save_path + '/WIP_m.png')