import os
import pandas as pd
import scipy.stats as st
import numpy as np
import simpy
import time
import functools

from SimComponents_rev import Source, Sink, Process, Monitor, Part

# 코드 실행 시작 시각
start_run = time.time()

# csv 파일 pandas 객체 생성 // 000, 003, fin 중 선택 가능
data_all = pd.read_csv('./data/PBS_assy_sequence_gen_fin.csv')
data = data_all[["product", "plate_weld", "saw_front", "turn_over", "saw_back", "longi_attach", "longi_weld", "sub_assy"]]

# process list
process_list = ["plate_weld", "saw_front", "turn_over", "saw_back", "longi_attach", "longi_weld", "sub_assy"]

# DATA PRE-PROCESSING
# part 정보

part = list(data["product"])
# 작업 정보, 7 = 공정 수 + Sink
columns = pd.MultiIndex.from_product([[i for i in range(len(process_list)+1)], ['start_time', 'process_time', 'process']])
df = pd.DataFrame(columns=columns, index=part)

IAT = st.expon.rvs(loc=3, scale=1, size=len(data))
start_time = IAT.cumsum()

parts = []
# process + Sink --> len(process_list) + 1
for i in range(len(process_list) + 1):
    # Sink 모델링
    if i == len(process_list):
        df[(i, 'start_time')] = None
        df[(i, 'process_time')] = None
        df[(i, 'process')] = 'Sink'
    # 공정 모델링
    else:
        df[(i, 'start_time')] = 0 if i!= 0 else start_time
        df[(i, 'process_time')] = list(data[process_list[i]])
        df[(i, 'process')] = process_list[i]

for i in range(len(df)):
    parts.append(Part(df.index[i], df.iloc[i]))
# tp_info = {}
# wf_info = {}
#
# tp_info["TP_1"] = {"capa":100, "v_loaded":0.5, "v_unloaded":1.0}
# tp_info["TP_2"] = {"capa":100, "v_loaded":0.3, "v_unloaded":0.8}
# tp_info["TP_3"] = {"capa":100, "v_loaded":0.2, "v_unloaded":0.7}
#
# wf_info["WF_1"] = {"skill":1.0}
# wf_info["WF_2"] = {"skill":1.2}

# Modeling
env = simpy.Environment()

##
model = {}
server_num = [1 for _ in range(len(process_list))]
filepath = './result/event_log_PBS_fin_tp.csv'
Monitor = Monitor(filepath)
# Resource = Resource(env, tp_info, wf_info, model, Monitor)
each_MTTF = functools.partial(np.random.exponential, 5)
each_MTTR = functools.partial(np.random.exponential, 3)
MTTR = {}
MTTF = {}
for process in process_list:
    if process == 'saw_front':
        MTTR[process] = [each_MTTR]
        MTTF[process] = [each_MTTF]
    else:
        MTTR[process] = [None]
        MTTF[process] = [None]


# Source
Source = Source(env, parts, model, Monitor)

# process modeling
for i in range(len(process_list) + 1):
    if i == len(process_list):
        model['Sink'] = Sink(env, Monitor)
    else:
        model[process_list[i]] = Process(env, process_list[i], server_num[i], model, Monitor, MTTR=MTTR, MTTF=MTTF)

# Simulation
start = time.time()  # 시뮬레이션 실행 시작 시각
env.run(until=1000)
finish = time.time()  # 시뮬레이션 실행 종료 시각

print('#' * 80)
print("Results of PBS simulation")
print('#' * 80)

# 코드 실행 시간
print("data pre-processing : ", start - start_run)
print("total time : ", finish - start_run)
print("simulation execution time :", finish - start)

print('#' * 80)
print("Makespan : ", model['Sink'].last_arrival)

event_tracer = Monitor.save_event_tracer()

