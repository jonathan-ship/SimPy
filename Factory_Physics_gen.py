import simpy
import random
import scipy.stats as st
import time
import os
from collections import OrderedDict
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from SimComponents import Source, Sink, Process, Monitor

'''
process list = [process1, process2]
각 기계수는 1대 
'''

if __name__ == '__main__':
    ## 블록 갯수
    blocks = 18000
    start_0 = time.time()

    start_time_1 = st.expon.rvs(loc=25, scale=1, size=blocks)
    start_time_1 = start_time_1.cumsum()

    process_time_1 = st.gamma.rvs(a=0.16, loc=0, scale=137.5, size=blocks)

    process_time_2 = st.gamma.rvs(a=1, loc=0, scale=23, size=blocks)

    def generator():
        for i in range(blocks):
            srs = pd.Series()

            temp_series_1 = pd.Series([start_time_1[i], process_time_1[i], 'process1'],
                                      index=[[0, 0, 0], ['start_time', 'process_time', 'process']])
            srs = pd.concat([srs, temp_series_1])

            temp_series_2 = pd.Series([0, process_time_2[i], 'process2'],
                                      index=[[1, 1, 1], ['start_time', 'process_time', 'process']])
            srs = pd.concat([srs, temp_series_2])

            temp_series_3 = pd.Series([None, None, 'Sink'],
                                      index=[[2, 2, 2], ['start_time', 'process_time', 'process']])
            srs = pd.concat([srs, temp_series_3])

            yield srs

    WIP_graph = False
    Throughput_graph = False
    save_graph = False

    if save_graph:
        save_path = './data/actual_data'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

    # samp_dist = functools.partial(random.expovariate, 1) # need to be checked
    samp_dist = 1

    ## 기계 수 조정
    m_1 = 1
    m_2 = 1

    m_dict = {'process1': m_1, 'process2': m_2}

    gen_block_data = generator()
    process_dict = {}

    # modeling
    env = simpy.Environment()
    Source = Source(env, 'Source', gen_block_data, process_dict, blocks, data_type="gen")
    Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)

    process_list = ['process1', 'process2']

    process = []
    monitor = []
    monitor_dict = {}

    ## Process 할당
    for i in range(len(process_list)):
        process.append(Process(env, process_list[i], m_dict[process_list[i]], process_dict, 10000))

    for i in range(len(process_list)):
        process_dict[process_list[i]] = process[i]

    process_dict['Sink'] = Sink

    Monitor1 = Monitor(env, process_dict['process1'], samp_dist)
    Monitor2 = Monitor(env, process_dict['process2'], samp_dist)

    # Run it
    start = time.time()
    env.run()
    finish = time.time()

    print('#' * 80)
    print("Results of simulation")
    print('#' * 80)

    # 코드 실행 시간
    print("data pre-processing : ", start - start_0)
    print("total time : ", finish - start_0)
    print("simulation execution time :", finish - start)

    # 총 리드타임 - 마지막 part가 Sink에 도달하는 시간
    print("Total Lead Time :", Sink.last_arrival)

    # 가동률
    def utilization(activity):
        temp_process = process_dict[activity]
        total_time = (temp_process.process_finish - temp_process.process_start) * temp_process.server_num
        total_working = temp_process.working_time
        u = total_working / total_time

        return u

    for process in process_list:
        print('utilization of {} : '.format(process), utilization(process))


    # 가동률
    print('Process 1 : ', np.mean(Monitor1.WIP))
    print('Process 2 : ', np.mean(Monitor2.WIP))
    print(np.mean(Monitor1.arrival_rate))


    # throughput and arrival_rate
    '''if Throughput_graph:
        smoothing = 1000
        throughput_1 = pd.Series(Monitor1.throughput).rolling(window=smoothing, min_periods=1).mean()
        throughput_2 = pd.Series(Monitor2.throughput).rolling(window=smoothing, min_periods=1).mean()
        arrival_rate_1 = pd.Series(Monitor1.arrival_rate).rolling(window=smoothing, min_periods=1).mean()
        arrival_rate_2 = pd.Series(Monitor2.arrival_rate).rolling(window=smoothing, min_periods=1).mean()

        fig, ax = plt.subplots(2, 1, squeeze=False)

        ax[0][0].plot(Monitor1.time, arrival_rate_1, label='arrival_rate')
        ax[0][0].plot(Monitor1.time, throughput_1, label='throughput')
        ax[1][0].plot(Monitor2.time, arrival_rate_2, label='arrival_rate')
        ax[1][0].plot(Monitor2.time, throughput_2, label='throughput')


        ax[0][0].set_xlabel('time[day]')
        ax[0][0].set_ylabel('rate[EA/day]')
        ax[1][0].set_xlabel('time[day]')
        ax[1][0].set_ylabel('rate[EA/day]')


        ax[0][0].set_title("Arrival_rate/Troughput - {0}".format(Monitor1.port.name))
        ax[1][0].set_title("Arrival_rate/Troughput - {0}".format(Monitor2.port.name))

        plt.legend()
        plt.tight_layout()
        plt.show()

        if save_graph:
            fig.savefig(save_path + '/ArrivalRate_Troughput.png')'''

    # WIP and m
    '''if WIP_graph:
        fig, ax = plt.subplots(2, 1, squeeze=False)

        ax[0][0].plot(Monitor1.time, Monitor1.WIP, label='WIP')
        ax[0][0].plot(Monitor1.time, Monitor1.M, label='m')
        ax[1][0].plot(Monitor2.time, Monitor2.WIP, label='WIP')
        ax[1][0].plot(Monitor2.time, Monitor2.M, label='m')

        ax[0][0].set_xlabel('time[day]')
        ax[0][0].set_ylabel('num')
        ax[1][0].set_xlabel('time[day]')
        ax[1][0].set_ylabel('num')

        ax[0][0].set_title("WIP/m - {0}".format(Monitor1.port.name))
        ax[1][0].set_title("WIP/m - {0}".format(Monitor2.port.name))

        plt.legend()
        plt.tight_layout()
        plt.show()

        if save_graph:
            fig.savefig(save_path + '/WIP_m.png')'''