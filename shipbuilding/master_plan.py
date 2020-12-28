import os
import pandas as pd
import numpy as np
import simpy
import time
import random
from datetime import datetime

from SimComponents import Source, Sink, Process, Monitor

# 코드 실행 시각
start_run = time.time()

## Pre-Processing
# DATA INPUT
data_all = pd.read_excel('../data/MCM_ACTIVITY.xls')
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

for block_code in block_list:
    temp = data[data['BLOCKCODE'] == block_code]
    temp_1 = temp.sort_values(by=['PLANSTARTDATE'], axis=0, inplace=False)
    temp = temp_1.reset_index(drop=True)
    df.loc[idx] = [None for _ in range(len(df.columns))]
    n = 0  # 저장된 공정 개수
    for i in range(0, len(temp)):
        activity = temp['ACTIVITY'][i]
        df.loc[idx][(n, 'start_time')] = temp['PLANSTARTDATE'][i]
        df.loc[idx][(n, 'process_time')] = temp['PLANDURATION'][i]
        df.loc[idx][(n, 'process')] = activity
        n += 1

    df.loc[idx][(n, 'process')] = 'Sink'
    idx += 1

df.sort_values(by=[(0, 'start_time')], axis=0, inplace=True)
df = df.reset_index(drop=True)
df = pd.concat([df_part, df], axis=1)

env = simpy.Environment()
model = {}
server_num = np.full(len(process_list), 1)

monitor = Monitor('../result/event_log_master_plan.csv')
source = Source(env, 'Source', df, model, monitor)
for i in range(len(process_list) + 1):
    if i == len(process_list):
        model['Sink'] = Sink(env, 'Sink', monitor)
    else:
        model[process_list[i]] = Process(env, process_list[i], server_num[i], model, monitor)

start = time.time()
env.run()
finish = time.time()
print('#' * 80)
print("Results of simulation")
print('#' * 80)


# 코드 실행 시간
print("data pre-processing : ", start - start_run)
print("simulation execution time :", finish - start)
print("total time : ", finish - start_run)

event_tracer = monitor.save_event_tracer()
