import simpy
import random
import functools
import time
import os
import scipy.stats as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from SimComponents import Sink, Process, Monitor, Source


if __name__ == "__main__":
    start_0 = time.time()
    #data pre-processing

    blocks = 18000
    blocks_1 = blocks + 1000  # 1000 = 음수 처리를 위한 여유분

    IAT = np.floor(st.chi2.rvs(df=1.53, loc=-0, scale=0.22, size=blocks))
    start_time_1 = IAT.cumsum()

    process_time_1 = np.round(st.exponnorm.rvs(K=7.71, loc=2.40, scale=1.70, size=blocks_1))
    process_time_1 = process_time_1[process_time_1 > 0][:blocks]

    process_time_2 = np.round(st.chi2.rvs(df=1.63, loc=1.00, scale=7.43, size=blocks_1))
    process_time_2 = process_time_2[process_time_2 > 0][:blocks]

    process_time_3 = np.round(st.exponnorm.rvs(K=1.75, loc=8.53, scale=2.63, size=blocks_1))
    process_time_3 = process_time_3[process_time_3 > 0][:blocks]

    def generator():
        for i in range(blocks):
            srs = pd.Series()

            temp_series_1 = pd.Series([start_time_1[i], process_time_1[i], 'Assembly'],
                                      index=[[0, 0, 0], ['start_time', 'process_time', 'process']])
            srs = pd.concat([srs, temp_series_1])

            temp_series_2 = pd.Series([0, process_time_2[i], 'Outfitting'],
                                      index=[[1, 1, 1], ['start_time', 'process_time', 'process']])
            srs = pd.concat([srs, temp_series_2])

            temp_series_3 = pd.Series([0, process_time_3[i], 'Painting'],
                                      index=[[2, 2, 2], ['start_time', 'process_time', 'process']])
            srs = pd.concat([srs, temp_series_3])

            temp_series_4 = pd.Series([None, None, 'Sink'],
                                      index=[[3, 3, 3], ['start_time', 'process_time', 'process']])
            srs = pd.concat([srs, temp_series_4])

            yield srs

    gen_block_data = generator()
    # modeling
    env = simpy.Environment()

    WIP_graph = False
    Throughput_graph = False
    save_graph = False

    if save_graph:
        save_path = './data/fitting_data'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

    # samp_dist = functools.partial(random.expovariate, 1)
    samp_dist = 1

    m_assy = 295
    m_oft = 285
    m_pnt = 232

    m_dict = {'Assembly': m_assy, 'Outfitting': m_oft, 'Painting': m_pnt}

    process_dict = {}

    # modeling
    env = simpy.Environment()
    Source = Source(env, 'Source', gen_block_data, process_dict, blocks, data_type="gen")
    Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)

    process = []
    monitor = []
    monitor_dict = {}
    process_list = ['Assembly', 'Outfitting', 'Painting']

    ## Process 할당
    for i in range(len(process_list)):
        process.append(Process(env, process_list[i], m_dict[process_list[i]], process_dict, 10000))

    for i in range(len(process_list)):
        process_dict[process_list[i]] = process[i]
    # Assembly = Process(env, "Assembly", m_assy, qlimit=10000)
    # Outfitting = Process(env, "Outfitting", m_oft, qlimit=10000)
    # Painting = Process(env, "Painting", m_pnt, qlimit=10000)

    process_dict['Sink'] = Sink

    Monitor1 = Monitor(env, process_dict['Assembly'], samp_dist)
    Monitor2 = Monitor(env, process_dict['Outfitting'], samp_dist)
    Monitor3 = Monitor(env, process_dict['Painting'], samp_dist)

    # Run it
    start = time.time()
    env.run()
    finish = time.time()

    print('#' * 80)
    print("Results of simulation")
    print('#' * 80)

    # 코드 실행 시간
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

    # throughput and arrival_rate
    if Throughput_graph:
        smoothing = 1000
        throughput_assy = pd.Series(Monitor1.throughput).rolling(window=smoothing, min_periods=1).mean()
        throughput_oft = pd.Series(Monitor2.throughput).rolling(window=smoothing, min_periods=1).mean()
        throughput_pnt = pd.Series(Monitor3.throughput).rolling(window=smoothing, min_periods=1).mean()
        arrival_rate_assy = pd.Series(Monitor1.arrival_rate).rolling(window=smoothing, min_periods=1).mean()
        arrival_rate_oft = pd.Series(Monitor2.arrival_rate).rolling(window=smoothing, min_periods=1).mean()
        arrival_rate_pnt = pd.Series(Monitor3.arrival_rate).rolling(window=smoothing, min_periods=1).mean()

        fig, ax = plt.subplots(3, 1, squeeze=False)

        ax[0][0].plot(Monitor1.time, arrival_rate_assy, label='arrival_rate')
        ax[0][0].plot(Monitor1.time, throughput_assy, label='throughput')
        ax[1][0].plot(Monitor2.time, arrival_rate_oft, label='arrival_rate')
        ax[1][0].plot(Monitor2.time, throughput_oft, label='throughput')
        ax[2][0].plot(Monitor3.time, arrival_rate_pnt, label='arrival_rate')
        ax[2][0].plot(Monitor3.time, throughput_pnt, label='throughput')

        ax[0][0].set_xlabel('time[day]')
        ax[0][0].set_ylabel('rate[EA/day]')
        ax[1][0].set_xlabel('time[day]')
        ax[1][0].set_ylabel('rate[EA/day]')
        ax[2][0].set_xlabel('time[day]')
        ax[2][0].set_ylabel('rate[EA/day]')

        ax[0][0].set_title("Arrival_rate/Throughput - {0}".format(Monitor1.port.name))
        ax[1][0].set_title("Arrival_rate/Throughput - {0}".format(Monitor2.port.name))
        ax[2][0].set_title("Arrival_rate/Throughput - {0}".format(Monitor3.port.name))

        plt.legend()
        plt.tight_layout()
        plt.show()

        if save_graph:
            fig.savefig(save_path + '/ArrivalRate_Throughput.png')

    # WIP and m
    if WIP_graph:
        fig, ax = plt.subplots(3, 1, squeeze=False)

        ax[0][0].plot(Monitor1.time, Monitor1.WIP, label='WIP')
        ax[0][0].plot(Monitor1.time, Monitor1.M, label='m')
        ax[1][0].plot(Monitor2.time, Monitor2.WIP, label='WIP')
        ax[1][0].plot(Monitor2.time, Monitor2.M, label='m')
        ax[2][0].plot(Monitor3.time, Monitor3.WIP, label='WIP')
        ax[2][0].plot(Monitor3.time, Monitor3.M, label='m')

        ax[0][0].set_xlabel('time[day]')
        ax[0][0].set_ylabel('num')
        ax[1][0].set_xlabel('time[day]')
        ax[1][0].set_ylabel('num')
        ax[2][0].set_xlabel('time[day]')
        ax[2][0].set_ylabel('num')

        ax[0][0].set_title("WIP/m - {0}".format(Monitor1.port.name))
        ax[1][0].set_title("WIP/m - {0}".format(Monitor2.port.name))
        ax[2][0].set_title("WIP/m - {0}".format(Monitor3.port.name))

        plt.legend()
        plt.tight_layout()
        plt.show()

        if save_graph:
            fig.savefig(save_path + '/WIP_m.png')