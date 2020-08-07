import simpy
import time
import os
import scipy.stats as st
import pandas as pd

from SimComponents_rev import Sink, Process, Source

# 코드 실행 시작 시각
start_0 = time.time()

# DATA PRE-PROCESSING
blocks = 1000  # 블록 수
df_part = pd.DataFrame([i for i in range(blocks)], columns=["part"])

process_list = ['process1', 'process2']
columns = pd.MultiIndex.from_product([[i for i in range(len(process_list)+1)], ['start_time', 'process_time', 'process']])
data = pd.DataFrame([], columns=columns)

# process 1
data[(0, 'start_time')] = st.expon.rvs(loc=25, scale=1, size=blocks)
data[(0, 'start_time')] = data[(0, 'start_time')].cumsum()
data[(0, 'process_time')] = st.gamma.rvs(a=0.16, loc=0, scale=137.5, size=blocks)
data[(0, 'process')] = 'process1'

# process 2
data[(1, 'start_time')] = 0
data[(1, 'process_time')] = st.gamma.rvs(a=1, loc=0, scale=23, size=blocks)
data[(1, 'process')] = 'process2'

# Sink
data[(2, 'start_time')] = None
data[(2, 'process_time')] = None
data[(2, 'process')] = 'Sink'

data = pd.concat([df_part, data], axis=1)

# Modeling
env = simpy.Environment()

##
event_tracer = pd.DataFrame(columns=["TIME", "EVENT", "PART", "PROCESS", "SERVER_ID"])
model = {}
server_num = [1 for _ in range(len(process_list))]

# Modeling
# Source
Source = Source(env, 'Source', data, model, event_tracer)

for i in range(len(process_list) + 1):
    if i == len(process_list):
        model['Sink'] = Sink(env, 'Sink')
    else:
        model[process_list[i]] = Process(env, process_list[i], server_num[i], model, event_tracer, qlimit=1)

# Run it
start = time.time()
env.run()
finish = time.time()

print('#' * 80)
print("Results of simulation")
print('#' * 80)

# 코드 실행 시간
print("data pre-processing : ", start - start_0)  # 시뮬레이션 시작 시각
print("total time : ", finish - start_0)
print("simulation execution time :", finish - start)  # 시뮬레이션 종료 시각



# save data
save_path = './result'
if not os.path.exists(save_path):
    os.makedirs(save_path)

# event tracer dataframe으로 변환
df_event_tracer = pd.DataFrame(event_tracer)
df_event_tracer.to_excel(save_path + '/event_Factory_Physics.xlsx')

