import os
import pandas as pd
import scipy.stats as st
import simpy
import time

from SimComponents_new import Source, Sink, Process, return_event_tracer

# 코드 실행 시작 시각
start_run = time.time()

# csv 파일 pandas 객체 생성 // 000, 003, fin 중 선택 가능
data_all = pd.read_csv('./data/PBS_assy_sequence_gen_fin.csv')
data = data_all[["product", "plate_weld", "saw_front", "turn_over", "saw_back", "longi_weld", "unit_assy", "sub_assy"]]

# process list
process_list = ["plate_weld", "saw_front", "turn_over", "saw_back", "longi_weld", "unit_assy", "sub_assy"]

# DATA PRE-PROCESSING
# part 정보
df_part = pd.DataFrame(data["product"])
df_part = df_part.rename(columns={"product": "part"})

# 작업 정보, 7 = 공정 수 + Sink
columns = pd.MultiIndex.from_product([[i for i in range(len(process_list)+1)], ['start_time', 'process_time', 'process']])
df = pd.DataFrame([], columns=columns)

IAT = st.expon.rvs(loc=3, scale=1, size=len(data))
start_time = IAT.cumsum()

for i in range(len(process_list) + 1):
    if i == len(process_list):  # Sink
        df[(i, 'start_time')] = None
        df[(i, 'process_time')] = None
        df[(i, 'process')] = 'Sink'
    else:  # 공정
        if i == 0:
            df[(i, 'start_time')] = start_time
        else:
            df[(i, 'start_time')] = 0

        df[(i, 'process_time')] = data[process_list[i]]
        df[(i, 'process')] = process_list[i]

df = pd.concat([df_part, df], axis=1)

# Modeling
env = simpy.Environment()

##
model = {}
server_num = [1 for _ in range(len(process_list))]

# Sink modeling

Source = Source(env, 'Source', df, model)
# process modeling
for i in range(len(process_list) + 1):
    if i == len(process_list):
        model['Sink'] = Sink(env, 'Sink')
    else:
        model[process_list[i]] = Process(env, process_list[i], server_num[i], model, qlimit=1)

# Simulation
start = time.time()  # 시뮬레이션 실행 시작 시각
env.run()
finish = time.time()  # 시뮬레이션 실행 종료 시각

print('#' * 80)
print("Results of simulation")
print('#' * 80)

# 코드 실행 시간
print("data pre-processing : ", start - start_run)
print("total time : ", finish - start_run)
print("simulation execution time :", finish - start)

# 총 리드타임 - 마지막 part가 Sink에 도달하는 시간

# save data
save_path = './result'
if not os.path.exists(save_path):
    os.makedirs(save_path)

# event tracer dataframe으로 변환
#df_event_tracer = pd.DataFrame(event_tracer)
df_event_tracer = pd.DataFrame(return_event_tracer())
df_event_tracer.to_excel(save_path +'/event_PBS_rev.xlsx')