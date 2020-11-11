import os
import pandas as pd
import numpy as np
import simpy
import time
import random

from SimComponents_rev import Source, Sink, Process_without_subprocess, Monitor

# 코드 실행 시각
start_run = time.time()

# DATA INPUT
data_all = pd.read_excel('./data/MCM_ACTIVITY.xls')
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



# 각 블록별 activity 개수
activity_num = []
for block_code in block_list:
    temp = data[data['BLOCKCODE'] == block_code]
    temp_1 = temp.sort_values(by=['PLANSTARTDATE'], axis=0, inplace=False)
    temp = temp_1.reset_index(drop=True, inplace=False)
    activity_num.append(len(temp))

max_num_of_activity = np.max(activity_num)

# S-Module에 넣어 줄 dataframe(중복된 작업시간 처리)
# 13 : 한 블록이 거치는 공정의 최대 개수(12) + Sink  --> 수정 필요
columns = pd.MultiIndex.from_product([[i for i in range(max_num_of_activity + 1)], ['start_time', 'process_time', 'process']])
df = pd.DataFrame([], columns=columns)
idx = 0  # df에 저장된 block 개수

for block_code in block_list:
    temp = data[data['BLOCKCODE'] == block_code]
    temp_1 = temp.sort_values(by=['PLANSTARTDATE'], axis=0, inplace=False)
    temp = temp_1.reset_index(drop=True)
    temp_list = []
    df.loc[block_code] = [None for _ in range(len(df.columns))]
    n = 0  # 저장된 공정 개수

    for i in range(0, len(temp) - 1):
        activity = temp['ACTIVITY'][i]
        date1 = temp['PLANFINISHDATE'][i]  # 선행공정 종료날짜
        date2 = temp['PLANSTARTDATE'][i+1]  # 후행공정 시작날짜
        date3 = temp['PLANFINISHDATE'][i+1]  # 후행공정 종료날짜

        if date1 > date2:  # 후행공정이 선행공정 종료 전에 시작할 때
            if date1 > date3:  # 후행공정이 선행공정에 포함될 때
                temp.loc[i+1, 'PLANDURATION'] = -1
            else:
                temp.loc[i+1, 'PLANDURATION'] -= date2 - date1

        if temp['PLANDURATION'][i] > 0:
            df.loc[block_code][n]['start_time'] = temp['PLANSTARTDATE'][i]
            df.loc[block_code][n]['process_time'] = temp['PLANDURATION'][i]
            df.loc[block_code][n]['process'] = activity
            n += 1

    if temp['PLANDURATION'][len(temp)-1] > 0:
        df.loc[block_code][n]['start_time'] = temp['PLANSTARTDATE'][len(temp)-1]
        df.loc[block_code][n]['process_time'] = temp['PLANDURATION'][len(temp)-1]
        df.loc[block_code][n]['process'] = temp['ACTIVITY'][len(temp)-1]
        n += 1

    df.loc[block_code][(n, 'process')] = 'Sink'

    # # temp = temp[temp['PLANDURATION'] >= 0]
    # idx += 1

df.sort_values(by=[(0, 'start_time')], axis=0, inplace=True)
# df = df.reset_index(drop=True)


# Modeling
env = simpy.Environment()

##
model = {}
server_num = [1 for _ in range(len(process_list))]
filename = './result/event_log_masterplan.csv'
Monitor = Monitor(filename)

# Source, Sink modeling
Source = Source(env, 'Source', df, model, Monitor)

# Process modeling
for i in range(len(process_list) + 1):
    if i == len(process_list):
        model['Sink'] = Sink(env, 'Sink', Monitor)
    else:
        model[process_list[i]] = Process_without_subprocess(env, process_list[i], server_num[i], model, Monitor, qlimit=1)

# Run it
df.to_excel('./master_plan_전처리.xlsx')
start = time.time()  # 시뮬레이션 시작 시각
env.run()
finish = time.time()  # 시뮬레이션 종료 시각

print('#' * 80)
print("Results of simulation")
print('#' * 80)

# 코드 실행 시간
print("data pre-processing : ", start - start_run)
print("simulation execution time :", finish - start)
print("total time : ", finish - start_run)

