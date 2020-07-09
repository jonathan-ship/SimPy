import os
import pandas as pd
import simpy
import time
import random

from SimComponents import Source, Sink, Process
from Postprocessing import Utilization, Queue

# 코드 실행 시각
start_0 = time.time()

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

df_part = pd.DataFrame(block_list, columns=["part"])

# raw data 저장 - block1(list)
# block1 = []
# activity_num = []
# for block_code in block_list:
#     temp = data[data['BLOCKCODE'] == block_code]
#     temp_1 = temp.sort_values(by=['PLANSTARTDATE'], axis=0, inplace=False)
#     temp = temp_1.reset_index(drop=True, inplace=False)
#
#     block1.append(temp)

# S-Module에 넣어 줄 dataframe(중복된 작업시간 처리)
# 13 : 한 블록이 거치는 공정의 최대 개수(12) + Sink
columns = pd.MultiIndex.from_product([[i for i in range(13)], ['start_time', 'process_time', 'process']])
df = pd.DataFrame([], columns=columns)
idx = 0  # df에 저장된 block 개수

for block_code in block_list:
    temp = data[data['BLOCKCODE'] == block_code]
    temp_1 = temp.sort_values(by=['PLANSTARTDATE'], axis=0, inplace=False)
    temp = temp_1.reset_index(drop=True)
    temp_list = []
    df.loc[idx] = [None for _ in range(len(df.columns))]
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
            df.loc[idx][n] = [temp['PLANSTARTDATE'][i], temp['PLANDURATION'][i], activity]
            n += 1

    if temp['PLANDURATION'][len(temp)-1] > 0:
        df.loc[idx][n] = [temp['PLANSTARTDATE'][len(temp)-1], temp['PLANDURATION'][len(temp)-1], temp['ACTIVITY'][len(temp)-1]]
        n += 1

    df.loc[idx][(n, 'process')] = 'Sink'

    # temp = temp[temp['PLANDURATION'] >= 0]
    idx += 1

df.sort_values(by=[(0, 'start_time')], axis=0, inplace=True)
df = df.reset_index(drop=True)

df = pd.concat([df_part, df], axis=1)

# Modeling
env = simpy.Environment()

##
event_tracer = {"event": [], "time": [], "part": [], "process": []}
process_dict = {}
process = []
m_dict = {}

# Source, Sink modeling
Source = Source(env, 'Source', df, process_dict, len(df), event_tracer=event_tracer,data_type="df")
Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)

# Process modeling
for i in range(len(process_list)):
    # 각 공정의 작업장 수 1~10
    m_dict[process_list[i]] = random.randrange(1, 6)
    # qlimit 5 / 10 바꿔가면서 run 해볼 것 / run 할 때마다 event tracer 파일 새로 생성됨
    process.append(Process(env, process_list[i], m_dict[process_list[i]], process_dict, event_tracer=event_tracer, qlimit=10))
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
df_event_tracer.to_excel(save_path +'/event_master_plan.xlsx')

# DATA POST-PROCESSING
# Event Tracer을 이용한 후처리
print('#' * 80)
print("Data Post-Processing")
print('#' * 80)

# UTILIZATION
# Utilization = Utilization(df_event_tracer, process_dict, process_list)
# Utilization.utilization()
# utilization = Utilization.u_dict
#
# for process in process_list:
#     print("utilization of {} : ".format(process), utilization[process])
