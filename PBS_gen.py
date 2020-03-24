import random
import pandas as pd
import scipy.stats as st
import simpy
from SimComponents import Source, Sink, Process, Monitor
import time

if __name__ == '__main__':
    start_0 = time.time()
    # csv 파일 pandas 객체 생성 // 000, 003, fin 중 선택 가능
    data_all = pd.read_csv('./data/PBS_assy_sequence_gen_fin.csv')
    data = data_all[["plate_weld", "saw_front", "turn_over", "saw_back", "longi_weld", "unit_assy", "sub_assy"]]

    process_list = ["plate_weld", "saw_front", "turn_over", "saw_back", "longi_weld", "unit_assy", "sub_assy"]

    IAT = st.expon.rvs(loc=3, scale=1, size=len(data))
    start_time_0 = IAT.cumsum()
    start_time_j = [0 for _ in range(len(data))]

    def generator(block_data):
        for i in range(len(block_data)):
            srs = pd.Series()
            for j in range(len(process_list)):
                start_time = start_time_0 if j == 0 else start_time_j

                temp_series = pd.Series([start_time[i], data[process_list[j]][i], process_list[j]],
                                        index=[[j, j, j], ['start_time', 'process_time', 'process']])
                srs = pd.concat([srs, temp_series])  # df에 추가

            # Sink 추가
            temp_series = pd.Series([None, None, 'Sink'],
                                    index=[[len(process_list) for _ in range(3)], ['start_time', 'process_time', 'process']])
            srs = pd.concat([srs, temp_series])
            yield srs


    gen_block_data = generator(data)

    env = simpy.Environment()

    process_dict = {}
    Source = Source(env, 'Source', gen_block_data, process_dict, len(data), data_type="gen")
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


