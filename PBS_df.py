import random
import pandas as pd
import scipy.stats as st
import functools
import simpy
from SimComponents import Source, Sink, Process, Monitor
import time

if __name__ == '__main__':
    start_0 = time.time()
    # csv 파일 pandas 객체 생성 // 000, 003, fin 중 선택 가능
    data_all = pd.read_csv('./data/PBS_assy_sequence_gen_fin.csv')
    data = data_all[["plate_weld", "saw_front", "turn_over", "saw_back", "longi_weld", "unit_assy", "sub_assy"]]

    process_list = ["plate_weld", "saw_front", "turn_over", "saw_back", "longi_weld", "unit_assy", "sub_assy"]

    # 7 = 공정 수 + Sink
    columns = pd.MultiIndex.from_product([[i for i in range(7)], ['start_time', 'process_time', 'process']])
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

    env = simpy.Environment()

    process_dict = {}
    Source = Source(env, 'Source', df, process_dict, len(df), data_type="df")
    Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)
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


