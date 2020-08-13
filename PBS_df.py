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
process_list = ["plate_weld", "saw_front", "turn_over", "saw_back", "longi_attach", "longi_weld", "sub_assy"]

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
Monitor = Monitor('event_log_PBS', len(df))

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

# 총 리드타임 - 마지막 part가 Sink에 도달하는 시간

# # save data
# save_path = './result'
# if not os.path.exists(save_path):
#     os.makedirs(save_path)
#
# # event tracer 저장
# event_tracer.to_excel(save_path +'/event_PBS_000.xlsx')
# print("Total Lead Time: ", model['Sink'].last_arrival)
#
# from PostProcessing_rev import Utilization, LeadTime, Idle, Throughput, Gantt, SUBWIP, WIP
# process_list_0 = ["plate_weld_0", "saw_front_0", "turn_over_0", "saw_back_0", "longi_attach_0", "longi_weld_0", "sub_assy_0"]
#
# #가동률 계산
# #Utilization = Utilization(event_tracer, model, "sub_assy")
# #util = Utilization.utilization()
# #print("Utilization = ", util)
#
# #Leadtime 계산
# Leadtime = LeadTime(event_tracer)
# lead = Leadtime.avg_LT()
# print("Leadtime = ", lead)
#
# #idle 계산
# #Idle = Idle(event_tracer, model, "sub_assy")
# #idle = Idle.idle()
# #print("Idle = ", idle)
#
# #Throughput 계산
# Throughput = Throughput(event_tracer, "sub_assy_0")
# th = Throughput.throughput()
# print("Throughput = ",th)
#
# #특정 시점 WIP 계산
# time = 100
# Wip = WIP(event_tracer, process_list_0, time)
# w = Wip.wip()
# print("WIP at",time," = ", w)
#
#
# #특정 시점 SubWIP 계산
# for i in range(len(process_list_0)):
#     Subwip = SUBWIP(event_tracer, process_list_0[i], time)
#     subwip = Subwip.subwip()
#     print("SubWIP of",process_list_0[i],"at", time, " = ", subwip)
#
# #Gantt Chart 그리기
# # process list
#
# Gantt = Gantt(event_tracer, process_list_0)
# gt = Gantt.gantt()
