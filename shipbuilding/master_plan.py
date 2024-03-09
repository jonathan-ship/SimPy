import os
import pandas as pd
import numpy as np
import simpy
import time
import random
from datetime import datetime
from collections import OrderedDict

from SimComponent.SimComponents import Source, Process, Sink, Monitor, Part
from PostProcessing import cal_wip, cal_utilization, cal_throughput, cal_leadtime

start_run = time.time()

# 코드 실행 시각

## Pre-Processing
# DATA INPUT
data_all = pd.read_excel('../data/master_planning.xlsx', engine = 'openpyxl')
data = data_all[['PROJECTNO', 'ACTIVITYCODE', 'LOCATIONCODE', 'PLANSTARTDATE', 'PLANFINISHDATE', 'PLANDURATION']]

# DATA PRE-PROCESSING
data = data[data['PLANSTARTDATE'].dt.year >= 2018]
data = data[data['LOCATIONCODE'] != 'OOO']

initial_date = data['PLANSTARTDATE'].min()

data['PLANSTARTDATE'] = data['PLANSTARTDATE'].apply(lambda x: (x - initial_date).days)
data['PLANFINISHDATE'] = data['PLANFINISHDATE'].apply(lambda x: (x - initial_date).days)
data['ACTIVITY'] = data['ACTIVITYCODE'].apply(lambda x: x[5:])
data['BLOCKCODE'] = data['PROJECTNO'] + ' ' + data['LOCATIONCODE']

process_list = list(data.drop_duplicates(['ACTIVITY'])['ACTIVITY'])
block_list = list(data.drop_duplicates(['BLOCKCODE'])['BLOCKCODE'])

df_part = pd.DataFrame(block_list, columns=["part"])

# 각 블록별 activity 개수
activity_num = []
for block_code in block_list:
    temp = data[data['BLOCKCODE'] == block_code]
    temp_1 = temp.sort_values(by=['PLANSTARTDATE'], axis=0, inplace=False)
    temp = temp_1.reset_index(drop=True, inplace=False)
    activity_num.append(len(temp))

## 최대 activity 개수
max_num_of_activity = np.max(activity_num)

# S-Module에 넣어 줄 dataframe(중복된 작업시간 처리)
columns = pd.MultiIndex.from_product([[i for i in range(max_num_of_activity + 1)], ['start_time', 'process_time', 'process']])
df = pd.DataFrame([], columns=columns)
idx = 0  # df에 저장된 block 개수
block_dict = dict()
for block_code in block_list:
    temp = data[data['BLOCKCODE'] == block_code]
    temp_1 = temp.sort_values(by=['PLANSTARTDATE'], axis=0, inplace=False)
    temp = temp_1.reset_index(drop=True)
    block_dict[block_code] = {"start_time": list(), "process_time": list(), "process": list()}
    # n = 0  # 저장된 공정 개수
    for i in range(0, len(temp)):
        activity = temp['ACTIVITY'][i]
        block_dict[block_code]['start_time'].append(temp['PLANSTARTDATE'][i])
        block_dict[block_code]['process_time'].append(temp['PLANDURATION'][i])
        block_dict[block_code]['process'].append(activity)
        # df.loc[block_code][(n, 'start_time')] = temp['PLANSTARTDATE'][i]
        # df.loc[block_code][(n, 'process_time')] = temp['PLANDURATION'][i]
        # df.loc[block_code][(n, 'process')] = activity
        # n += 1
    block_dict[block_code]['start_time'].append(None)
    block_dict[block_code]['process_time'].append(None)
    block_dict[block_code]['process'].append("Sink")
    #df.loc[block_code][(n, 'process')] = 'Sink'

# df.sort_values(by=[(0, 'start_time')], axis=0, inplace=True)
block_dict = sorted(block_dict.items(), key=lambda x: x[1]['start_time'][0])
block_dict = OrderedDict(block_dict)
parts = []

for block_code in block_dict:
    parts.append(Part(block_code, block_dict[block_code]))

env = simpy.Environment()
model = {}
server_num = np.full(len(process_list), 1)

Monitor = Monitor('../result/event_log_master_plan_with_tp_df.csv')
Source = Source(env, parts, model, Monitor)
###################
# transporter 사용 시 True, 아니면 False
network_using = True

if network_using:
    # network -> distance data
    # network_dist = pd.read_excel('../network/distance_data_masterplan.xlsx')
    # network_dist = network_dist.set_index('Unnamed: 0', drop=True)
    # # Resource
    # tp_info = {}
    # tp_num = 100
    # for i in range(tp_num):
    #     tp_info["TP_{0}".format(i+1)] = {"capa": 100, "v_loaded": 0.5, "v_unloaded": 1.0}
    # Resource = Resource(env, model, Monitor, tp_info=tp_info, network=network_dist)

    for i in range(len(process_list) + 1):
        if i == len(process_list):
            model['Sink'] = Sink(env, Monitor)
        else:
            model[process_list[i]] = Process(env, process_list[i], server_num[i], model, Monitor)
else:
    for i in range(len(process_list) + 1):
        if i == len(process_list):
            model['Sink'] = Sink(env, Monitor)
        else:
            model[process_list[i]] = Process(env, process_list[i], server_num[i], model, Monitor)

# recording time
start = time.time()
env.run()
finish = time.time()

event_tracer = Monitor.save_event_tracer()

# # result of each precess
# wip = 0.0
# for i in range(len(process_list)):
#     wip_i = cal_wip(event_tracer, process_list[i], 'Process', mode='p',
#                   start_time=0.0, finish_time=model['Sink'].last_arrival, step=100, save=True, filepath='../result')
#     print('#' * 80)
#     print('WIP of ', process_list[i])
#     print(wip_i)
#     wip += wip_i['WIP'][98]
#
# for i in range(len(process_list)):
#     TH = cal_throughput(event_tracer, process_list[i], 'Process', mode='p',
#                         start_time=0.0, finish_time=model['Sink'].last_arrival, step=100, save=True, filepath='../result')
#     print('#' * 80)
#     print('Throughput of ', process_list[i])
#     print(TH)
#
# for i in range(len(process_list)):
#     CT = cal_leadtime(event_tracer, process_list[i], 'Process', mode='p',
#                       start_time=0.0, finish_time=model['Sink'].last_arrival)
#     print('#' * 80)
#     print('Leadtime of ', process_list[i])
#     print(CT)
#
# for i in range(len(process_list)):
#     u, idel, working_time = cal_utilization(event_tracer, process_list[i], 'Process', num=server_num[i],
#                                             start_time=0.0, finish_time=model['Sink'].last_arrival, step=100, save=True, filepath='../result')
#     print('#' * 80)
#     print('Utilization of', process_list[i])
#     print(u)
#
#
# # result of the system
# CT = cal_leadtime(event_tracer, process_list[i], 'Process', mode='m',
#                   start_time=0.0, finish_time=model['Sink'].last_arrival)
#
# TH_sys = 0.0
# for i in range(len(process_list)):
#     TH = cal_throughput(event_tracer, process_list[i], 'Process', mode='m',
#                         start_time=0.0, finish_time=model['Sink'].last_arrival)
#     TH_sys += TH
#
# # 코드 실행 시간
# print('#' * 80)
# print("Results of simulation")
# print('#' * 80)
# print("data pre-processing : ", start - start_run)
# print("simulation execution time :", finish - start)
# print("total time : ", finish - start_run)
#
# print('#' * 80)
# print('WIP of the system: ', wip)
# print('Leadtime of the system: ', CT)
# print('Throughput of the system: ', TH_sys)