import pandas as pd
import simpy
import random
from SimComponents import Source, Sink, Process
import time
import numpy as np

start_0 = time.time()

data = pd.read_excel('./data/MCM_ACTIVITY.xls')
data = data[['PROJECTNO', 'ACTIVITYCODE', 'LOCATIONCODE', 'PLANSTARTDATE', 'PLANDURATION']]

data = data[data['PLANSTARTDATE'].dt.year >= 2018]
data = data[data['LOCATIONCODE'] != 'OOO']

initial_date = data['PLANSTARTDATE'].min()

data['PLANSTARTDATE'] = data['PLANSTARTDATE'].apply(lambda x: (x - initial_date).days)
data['ACTIVITY'] = data['ACTIVITYCODE'].apply(lambda x: x[5:])
data['BLOCKCODE'] = data['PROJECTNO'] + ' ' + data['LOCATIONCODE']

data_len = len(data)

block_list = []
activity_list = []
for i in range(data_len):
    temp = data.iloc[i]
    if temp['BLOCKCODE'] not in block_list:
        block_list.append(temp['BLOCKCODE'])
    if temp['ACTIVITY'] not in activity_list:
        activity_list.append(temp['ACTIVITY'])

## raw data 저장
# block1 = []  # 가공 전
# for block_code in block_list:
#     temp = data[data['BLOCKCODE'] == block_code]
#     temp.sort_values(by=['PLANSTARTDATE'], axis=0, inplace=True)
#     temp = temp.reset_index(drop=True)
#     block1.append(temp)

block2 = []  # 가공 후 블록 저장
for block_code in block_list:
    for_start = time.time()
    temp = data[data['BLOCKCODE'] == block_code]
    temp_1 = temp.sort_values(by=['PLANSTARTDATE'], axis=0, inplace=True)
    temp = temp_1.reset_index(drop=True)

    for i in range(0, len(temp) -1):
        date1 = temp['PLANSTARTDATE'][i] + temp['PLANDURATION'][i] - 1  #선행공정 종료날짜
        date2 = temp['PLANSTARTDATE'][i+1]  #후행공정 시작날짜
        date3 = temp['PLANSTARTDATE'][i+1] + temp['PLANDURATION'][i+1] - 1  #후행공정 종료날짜

        if date1 > date2:  #후행공정이 선행공정 종료 전에 시작할 때
            if date1 > date3:  #후행공정이 선행공정에 포함될 때
                temp.loc[i+1, 'PLANDURATION'] = -1
            else:
                temp.loc[i+1, 'PLANDURATION'] -= date2 - date1

    temp = temp[temp['PLANDURATION'] >= 0]
    block2.append(temp)

block2 = sorted(block2, key=lambda x: x.iloc[0]['PLANSTARTDATE'])  # 첫 번째 공정 시작 시간 순서대로 정렬


def generator(block_data):
    for i in range(len(block_data)):
        srs = pd.Series()
        project = block_data[i]
        for j in range(len(project)):
            temp_project = project.iloc[j]

            temp_series = pd.Series([temp_project['PLANSTARTDATE'], temp_project['PLANDURATION'], temp_project['ACTIVITY']],
                                index=[[j, j, j], ['start_time', 'process_time', 'process']])
            srs = pd.concat([srs, temp_series])  # df에 추가

        # Sink 추가
        temp_series = pd.Series([None, None, 'Sink'], index=[[len(project) for _ in range(3)], ['start_time', 'process_time', 'process']])
        srs = pd.concat([srs, temp_series])
        yield srs

gen_block_data = generator(block2)


# Simulation
RUN_TIME = 45000

env = simpy.Environment()

process_dict = {}
Source = Source(env, "Source", gen_block_data, process_dict, len(block2), data_type="gen")
Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)

process = []
for i in range(len(activity_list)):
    process.append(Process(env, activity_list[i], 10, process_dict, 10000))

for i in range(len(activity_list)):
    process_dict[activity_list[i]] = process[i]

process_dict['Sink'] = Sink

start = time.time()
env.run()
finish = time.time()

print('#'*80)
print("Results of simulation")
print('#'*80)
print("total time ", finish - start_0)
print("simulation execution time : ", finish - start)


## post-processing
'''def utilization(activity, m):
    temp_process = process_dict[activity]
    total_time = (temp_process.process_finish - temp_process.process_start) * m
    total_working = dict_activity[activity]['total working time']
    u = total_working / total_time

    return u

# 공정 별 working time 합
dict_activity = {}
for activity in activity_list:
    temp = data[data['ACTIVITY'] == activity]
    sum = temp['PLANDURATION'].sum()
    dict_activity[activity] = {}
    dict_activity[activity]['total working time'] = sum

    dict_activity[activity]['u'] = utilization(activity, 10)

    dict_activity[activity]['m'] = 1

count = 0
count2 = 0
print(len(activity_list))
while count < 24:
    for activity in activity_list:
        if dict_activity[activity]['u'] < 0.85:
            if dict_activity[activity]['m'] > 1:
                process_dict[activity].server_num -= 1
                dict_activity[activity]['m'] -= 1
        elif dict_activity[activity]['u'] > 0.95:
            process_dict[activity].server_num += 1
            dict_activity[activity]['m'] += 1

    env.run()
    count2 += 1

    count = 0
    for activity in activity_list:
        dict_activity[activity]['u'] = utilization(activity, dict_activity[activity]['m'])

        if (dict_activity[activity]['u'] <= 0.95) and (dict_activity[activity]['u'] >= 0.85):
            count += 1

    print(count, ' ', count2)

    if count == 8:
        print((pd.DataFrame.from_dict(dict_activity)).T)
    if count2 > 15:
        count = 24

m_list = [11,2,4,2,2,8,1,2,5,10,10,1,1,2,3,2,1,6,7,3,2,2,2,1]
for i in range(len(activity_list)):
    dict_activity[activity_list[i]]['m'] = m_list[i]

for activity in activity_list:
    dict_activity[activity]['u'] = utilization(activity, dict_activity[activity]['m'])

for activity in activity_list:
    dict_activity[activity]['u'] = utilization(activity, dict_activity[activity]['m'])

print((pd.DataFrame.from_dict(dict_activity)).T)
result = Sink.block_project_sim
df_result = pd.DataFrame(columns=['PROJECTNO', 'LOCATIONCODE', 'PLANSTARTDATE', 'PLANDURATION', 'ACTIVITY', 'BLOCKCODE'])

for part_name in result.keys():
    temp_dict = {}
    for activity_code in result[proj_no][location_code].keys():
        temp_dict['PROJECTNO'] = proj_no
        temp_dict['LOCATIONCODE'] = location_code
        temp_dict['PLANSTARTDATE'] = result[proj_no][location_code][activity_code][0]
        temp_dict['PLANDURATION'] = result[proj_no][location_code][activity_code][1]
        temp_dict['ACTIVITY'] = activity_code
        temp_dict['BLOCKCODE'] = proj_no + ' ' + location_code



# print(Sink.block_project_sim)'''