import simpy
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from SimComponents import Source, Sink, Process, Monitor
import scipy.stats as st

start_0 = time.time()
data_all = pd.read_excel('./data/spool_data_for_simulation.xlsx')
data_all = data_all[['NO_SPOOL', '제작협력사', '도장협력사', "Plan_makingLT", "Actual_makingLT", "Predicted_makingLT",
                 "Plan_paintingLT", "Actual_paintingLT", "Predicted_paintingLT"]]

data = data_all.rename(columns={'제작협력사': 'process1', '도장협력사': 'process2'}, inplace=False)
data['process1'] = data['process1'] + '_1'
data['process2'] = data['process2'] + '_2'

## IAT
# adist = functools.partial(random.randrange, 1, 10)
IAT = st.expon.rvs(loc=28, scale=1, size=len(data))  # 첫 번째 공정의 작업시간의 평균 = 27.9
start_time = IAT.cumsum()

def generator(block_data):
    for i in range(len(block_data)):
        srs = pd.Series()
        temp_block_data = block_data.iloc[i]

        ## process time : Plan_makingLT, Actual_makingLT, Predicted_makingLT 중 선택 가능
        temp_series_1 = pd.Series([start_time[i], temp_block_data['Actual_makingLT'], temp_block_data['process1']],
                                  index=[[0, 0, 0], ['start_time', 'process_time', 'process']])
        srs = pd.concat([srs, temp_series_1])

        temp_series_2 = pd.Series([0, temp_block_data['Actual_paintingLT'], temp_block_data['process2']],
                                  index=[[1, 1, 1], ['start_time', 'process_time', 'process']])
        srs = pd.concat([srs, temp_series_2])

        temp_series_3 = pd.Series([None, None, 'Sink'], index=[[2, 2, 2], ['start_time', 'process_time', 'process']])
        srs = pd.concat([srs, temp_series_3])

        yield srs


gen_block_data = generator(data)

RUN_TIME = 45000

env = simpy.Environment()

process_dict = {}
Source = Source(env, 'Source', gen_block_data, process_dict, len(data), data_type="gen")
Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)

process_list = list(data.drop_duplicates(['process1'])['process1'])
process_list += list(data.drop_duplicates(['process2'])['process2'])

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
print("simulation execution time : ", finish - start)


def utilization(activity):
    temp_process = process_dict[activity]
    total_time = (temp_process.process_finish - temp_process.process_start) * temp_process.server_num
    total_working = temp_process.working_time
    u = total_working / total_time

    return u


for process in process_list:
    print('utilization of {} : '.format(process), utilization(process))

