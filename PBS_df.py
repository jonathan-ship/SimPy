import os
import pandas as pd
import scipy.stats as st
import simpy
import time

from SimComponents_rev import Source, Sink, Process, Monitor

# 코드 실행 시작 시각
start_run = time.time()

# csv 파일 pandas 객체 생성 // 000, 003, fin 중 선택 가능
data_all = pd.read_csv('./data/PBS_assy_sequence_gen_fin.csv')
data = data_all[["product", "plate_weld", "saw_front", "turn_over", "saw_back", "longi_attach", "longi_weld", "sub_assy"]]

# process list
process_list = ["plate_weld", "saw_front", "saw_back", "longi_attach", "longi_weld", "sub_assy"]

# DATA PRE-PROCESSING
# part 정보
df_part = pd.DataFrame(data["product"])
df_part = df_part.rename(columns={"product": "part"})

# 작업 정보, 7 = 공정 수 + Sink
columns = pd.MultiIndex.from_product([[i for i in range(len(process_list)+1)], ['start_time', 'process_time', 'process']])
df = pd.DataFrame([], columns=columns)

# IAT = st.expon.rvs(loc=3, scale=1, size=len(data))
# start_time = IAT.cumsum()

for i in range(len(process_list) + 1):
    if i == len(process_list):  # Sink
        df[(i, 'start_time')] = None
        df[(i, 'process_time')] = None
        df[(i, 'process')] = 'Sink'
    else:  # 공정
        df[(i, 'start_time')] = 0
        df[(i, 'process_time')] = data[process_list[i]]
        df[(i, 'process')] = process_list[i]

df = pd.concat([df_part, df], axis=1)

# Modeling
env = simpy.Environment()

##
model = {}
server_num = [1 for _ in range(len(process_list))]
filename = './result/event_log_PBS.csv'
Monitor = Monitor(filename, len(df))

# Modeling
# Source
Source = Source(env, 'Source', df, model, Monitor)

# process modeling
for i in range(len(process_list) + 1):
    if i == len(process_list):
        model['Sink'] = Sink(env, 'Sink', Monitor)
    else:
        model[process_list[i]] = Process(env, process_list[i], server_num[i], model, Monitor, qlimit=1)

# Simulation
start = time.time()  # 시뮬레이션 실행 시작 시각
env.run()
finish = time.time()  # 시뮬레이션 실행 종료 시각

print('#' * 80)
print("Results of PBS simulation")
print('#' * 80)

# 코드 실행 시간
print("data pre-processing : ", start - start_run)
print("total time : ", finish - start_run)
print("simulation execution time :", finish - start)

print('#' * 80)
from PostProcessing_rev import Utilization, WIP
event_tracer = pd.read_csv(filename)
for process in process_list:
    util = Utilization(event_tracer, model, process, model['Sink'].last_arrival)
    u, _, _ = util.utilization()
    print("utilization of {0}: ".format(process), u)

