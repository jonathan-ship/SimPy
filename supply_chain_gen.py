import simpy
import random
import functools
import time
import os
import pandas as pd
from collections import OrderedDict
import matplotlib.pyplot as plt
from SimComponents import Source, Sink, Process, Monitor

start_0 = time.time()
data_all = pd.read_excel('./data/spool_data_for_simulation.xlsx')
data = data_all[['NO_SPOOL', '제작협력사', '도장협력사', "Plan_makingLT", "Actual_makingLT", "Predicted_makingLT",
                 "Plan_paintingLT", "Actual_paintingLT", "Predicted_paintingLT"]]

df = pd.DataFrame()
# df['part_no'] = data['NO_SPOOL']
df['process1'] = data['제작협력사'] + '_1'
df['process2'] = data['도장협력사'] + '_2'

# process time : plan, actual, predicted로 변경 가능
df['proc_time_1'] = data['Actual_makingLT']
df['proc_time_2'] = data['Actual_paintingLT']

## IAT
adist = functools.partial(random.randrange, 1, 10)

def generator(block_data):
    start_time = 0
    for i in range(len(block_data)):
        srs = pd.Series()
        temp_block_data = block_data.iloc[i]

        start_time += adist()
        temp_series_1 = pd.Series([start_time, temp_block_data['proc_time_1'], temp_block_data['process1']],
                                  index=[[0, 0, 0], ['start_time', 'process_time', 'process']])
        srs = pd.concat([srs, temp_series_1])

        temp_series_2 = pd.Series([start_time, temp_block_data['proc_time_2'], temp_block_data['process2']],
                                  index=[[1, 1, 1], ['start_time', 'process_time', 'process']])
        srs = pd.concat([srs, temp_series_2])

        temp_series_3 = pd.Series([None, None, 'Sink'], index=[[2, 2, 2], ['start_time', 'process_time', 'process']])
        srs = pd.concat([srs, temp_series_3])

        yield srs


gen_block_data = generator(df)

RUN_TIME = 45000

env = simpy.Environment()

process_dict = {}
Source = Source(env, 'Source', gen_block_data, process_dict, len(df), data_type="gen")
Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)

process_list = list(df.drop_duplicates(['process1'])['process1'])
process_list += list(df.drop_duplicates(['process2'])['process2'])

process = []
for i in range(len(process_list)):
    process.append(Process(env, process_list[i], 1, process_dict, 10000))

for i in range(len(process_list)):
    process_dict[process_list[i]] = process[i]

process_dict['Sink'] = Sink


start = time.time()
env.run()
finish = time.time()

print("total time ", finish - start_0)
print("simulation time : ", finish - start)


def utilization(activity):
    temp_process = process_dict[activity]
    total_time = (temp_process.process_finish - temp_process.process_start) * temp_process.server_num
    total_working = temp_process.working_time
    u = total_working / total_time

    return u


for process in process_list:
    print('utilization of {} : '.format(process), utilization(process))

