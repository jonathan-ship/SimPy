import simpy
import time
import pandas as pd
import scipy.stats as st
import matplotlib.pyplot as plt
from SimComponents import Source, Sink, Process, Monitor

start_0 = time.time()
data_all = pd.read_excel('./data/spool_data_for_simulation.xlsx')
data = data_all[['NO_SPOOL', '제작협력사', '도장협력사', "Plan_makingLT", "Actual_makingLT", "Predicted_makingLT",
                 "Plan_paintingLT", "Actual_paintingLT", "Predicted_paintingLT"]]

# df['part_no'] = data['NO_SPOOL']
data.rename(columns={'제작협력사': 'process1', '도장협력사': 'process2'}, inplace=True)
data['process1'] = data['process1'] + '_1'
data['process2'] = data['process2'] + '_2'

## IAT
# adist = functools.partial(random.randrange, 1, 10)
IAT = st.expon.rvs(loc=28, scale=1, size=len(data))  # 첫 번째 공정의 작업시간의 평균 = 27.9
start_time = IAT.cumsum()

# Source에 넣어 줄 dataframe
columns = pd.MultiIndex.from_product([[0, 1, 2], ['start_time', 'process_time', 'process']])
df = pd.DataFrame([], columns=columns)

# start_time
df[(0, 'start_time')] = start_time
df[(1, 'start_time')] = 0
df[(2, 'start_time')] = None

# process_time - Plan, Actual, Predicted 중 선택
df[(0, 'process_time')] = data['Actual_makingLT']
df[(1, 'process_time')] = data['Actual_paintingLT']
df[(2, 'process_time')] = None

# process
df[(0, 'process')] = data['process1']
df[(1, 'process')] = data['process2']
df[(2, 'process')] = 'Sink'

# Simulation
RUN_TIME = 45000

env = simpy.Environment()

process_dict = {}
Source = Source(env, 'Source', df, process_dict, len(df), data_type="df")
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
print("simulation time : ", finish - start)


def utilization(activity):
    temp_process = process_dict[activity]
    total_time = (temp_process.process_finish - temp_process.process_start) * temp_process.server_num
    total_working = temp_process.working_time
    u = total_working / total_time

    return u


for process in process_list:
    print('utilization of {} : '.format(process), utilization(process))

