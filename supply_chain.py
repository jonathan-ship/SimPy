import simpy
import random
import functools
import time
import os
import pandas as pd
from collections import OrderedDict
import matplotlib.pyplot as plt
from SimComponents_master_plan import DataframeSource, Sink, Process, Monitor

data_all = pd.read_excel('./data/spool_data_for_simulation.xlsx')
data = data_all[['NO_SPOOL', '제작협력사', '도장협력사', "Plan_makingLT", "Actual_makingLT", "Predicted_makingLT",
                 "Plan_paintingLT", "Actual_paintingLT", "Predicted_paintingLT"]]

df = pd.DataFrame()
df['part_no'] = data['NO_SPOOL']
df['process1'] = data['제작협력사'] + '_1'
df['process2'] = data['도장협력사'] + '_2'

# process time : plan, actual, predicted로 변경 가능
df['proc_time_1'] = data['Actual_makingLT']
df['proc_time_2'] = data['Actual_paintingLT']

adist = functools.partial(random.randrange, 1, 10)

def generator(block_data):
    for i in range(len(block_data)):
        temp_block_data = block_data.iloc[i]
        part_name = temp_block_data['part_no']

        dict_activity = OrderedDict()
        dict_activity[temp_block_data['process1']] = [adist(), temp_block_data['proc_time_1']]
        dict_activity[temp_block_data['process2']] = [0, temp_block_data['proc_time_2']]

        yield [part_name, dict_activity]


gen_block_data = generator(df)

RUN_TIME = 45000

env = simpy.Environment()

process_dict = {}
Source = DataframeSource(env, 'Source', gen_block_data, process_dict, len(df))
Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)

process_list = list(df.drop_duplicates(['process1'])['process1'])
process_list += list(df.drop_duplicates(['process2'])['process2'])

process = []
monitor = []
monitor_dict = {}
for i in range(len(process_list)):
    process.append(Process(env, process_list[i], 1, process_dict, 10000))

'''for i in range(len(process_list)):
    monitor.append(Monitor(env, process[i], 10))'''

for i in range(len(process_list)):
    process_dict[process_list[i]] = process[i]
    # monitor_dict[process_list[i]] = monitor[i]

process_dict['Sink'] = Sink


start = time.time()
env.run()
finish = time.time()

print(finish - start)
# print(Sink.block_project_sim)


def utilization(activity, m):
    temp_process = process_dict[activity]
    total_time = (temp_process.process_finish - temp_process.process_start) * m
    total_working = dict_activity[activity]['total working time']
    u = total_working / total_time

    return u


dict_activity = {}
for process in process_list:
    temp = df[(df['process1'] == process) | (df['process2'] == process)]
    if process[-1] == 1:
        sum = temp['proc_time_1'].sum()
    else:
        sum = temp['proc_time_2'].sum()
    dict_activity[process] = {}
    dict_activity[process]['total working time'] = sum

    dict_activity[process]['u'] = utilization(process, 1)

    dict_activity[process]['m'] = 1

for process in process_list:
    print('utilization of {} : '.format(process), dict_activity[process]['u'])

