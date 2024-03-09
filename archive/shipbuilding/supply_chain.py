import os
import simpy
import time
import pandas as pd
import scipy.stats as st

from SimComponent.SimComponents import Source, Sink, Process, Monitor, Part

# 코드 실행 시작 시각
start_0 = time.time()

# DATA INPUT
data_all = pd.read_excel('../data/spool_data_for_simulation.xlsx')
data_all = data_all[['NO_SPOOL', '제작협력사', '도장협력사', "Plan_makingLT", "Actual_makingLT", "Predicted_makingLT",
                 "Plan_paintingLT", "Actual_paintingLT", "Predicted_paintingLT"]]

data = data_all.rename(columns={'제작협력사': 'process1', '도장협력사': 'process2', 'NO_SPOOL': 'part'}, inplace=False)
data['process1'] = data['process1'] + '_1'
data['process2'] = data['process2'] + '_2'

# DATA PRE-PROCESSING
# part 정보
part = list(data["part"])

# 작업 정보
columns = pd.MultiIndex.from_product([[0, 1, 2], ['start_time', 'process_time', 'process']])
df = pd.DataFrame([], columns=columns, index=part)

# start_time
# IAT
IAT = st.expon.rvs(loc=28, scale=1, size=len(data))  # 첫 번째 공정의 작업시간의 평균 = 27.9
start_time = IAT.cumsum()

df[(0, 'start_time')] = 0
df[(1, 'start_time')] = 0
df[(2, 'start_time')] = None

# process_time - Plan, Actual, Predicted 중 선택
df[(0, 'process_time')] = list(data['Actual_makingLT'])
df[(1, 'process_time')] = list(data['Actual_paintingLT'])
df[(2, 'process_time')] = None

# process
df[(0, 'process')] = list(data['process1'])
df[(1, 'process')] = list(data['process2'])
df[(2, 'process')] = 'Sink'

parts = []
for i in range(len(df)):
    parts.append(Part(df.index[i], df.iloc[i]))

# Modeling
env = simpy.Environment()

##
process_list = list(data.drop_duplicates(['process1'])['process1'])
process_list += list(data.drop_duplicates(['process2'])['process2'])

model = {}
server_num = [1 for _ in range(len(process_list))]

filepath = '../result/event_log_supply_chain.csv'
Monitor = Monitor(filepath)

Source = Source(env, parts, model, Monitor)

# process modeling
for i in range(len(process_list) + 1):
    if i == len(process_list):
        model['Sink'] = Sink(env, Monitor)
    else:
        model[process_list[i]] = Process(env, process_list[i], server_num[i], model, Monitor, capacity=1)

# Simulation
start = time.time()  # 시뮬레이션 실행 시작 시각
env.run()
finish = time.time()  # 시뮬레이션 실행 종료 시각

print('#' * 80)
print("Results of simulation")
print('#' * 80)

# 코드 실행 시간
print("data pre-processing : ", start - start_0)
print("total time : ", finish - start_0)
print("simulation execution time :", finish - start)

event_tracer = Monitor.save_event_tracer()