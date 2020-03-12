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
    #data pre-processing
    columns = pd.MultiIndex.from_product([['Assembly', 'Outfitting', 'Painting'], ['start_time', 'process_time']])
    data = pd.DataFrame([], columns=columns)

    blocks = 18000
    start_time_assy, start_time_oft, start_time_pnt = 0.0, 0.0, 0.0
    for i in range(blocks):
        if i == 0:
            start_time_assy += 0.0
        else:
            start_time_assy += np.floor(st.chi2.rvs(df=1.53, loc=-0, scale=0.22))

        process_time_assy, process_time_oft, process_time_pnt = 0.0, 0.0, 0.0
        while process_time_assy <= 0:
            process_time_assy = np.round(st.exponnorm.rvs(K=7.71, loc=2.40, scale=1.70))
        while process_time_oft <= 0:
            process_time_oft = np.round(st.chi2.rvs(df=1.63, loc=1.00, scale=7.43))
        while process_time_pnt <= 0:
            process_time_pnt = np.round(st.exponnorm.rvs(K=1.75, loc=8.53, scale=2.63))

        data.loc[i] = [start_time_assy, process_time_assy, start_time_oft, process_time_oft, start_time_pnt, process_time_pnt]

    # modeling
    env = simpy.Environment()

    WIP_graph = True
    Throughput_graph = True
    save_graph = True

    if save_graph:
        save_path = './data/fitting_data'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

    # samp_dist = functools.partial(random.expovariate, 1)
    samp_dist = 1

    m_assy = 295
    m_oft = 285
    m_pnt = 232

    Source = Source(env, "Source", data)
    Sink = Sink(env, "Sink", rec_lead_time=True, rec_arrivals=True)
    Assembly = Process(env, "Assembly", m_assy, qlimit=10000)  # 조립 공정 작업장 수 = 200
    Outfitting = Process(env, "Outfitting", m_oft, qlimit=10000)  # 의장 공정 작업장 수 = 185
    Painting = Process(env, "Painting", m_pnt, qlimit=10000)  # 도장 공정 작업장 수 = 155

    Monitor1 = Monitor(env, Assembly, samp_dist)
    Monitor2 = Monitor(env, Outfitting, samp_dist)
    Monitor3 = Monitor(env, Painting, samp_dist)

    Source.out = Assembly
    Assembly.out = Outfitting
    Outfitting.out = Painting
    Painting.out = Sink

    # Run it
    start = time.time()
    env.run()
    finish = time.time()

    print('#' * 80)
    print("Results of simulation")
    print('#' * 80)

    # 코드 실행 시간
    print("simulation execution time :", finish - start)

    # 총 리드타임 - 마지막 part가 Sink에 도달하는 시간
    print("Total Lead Time :", Sink.last_arrival)

    # 가동률
    print("utilization of Assembly : {}".format(Monitor1.u))
    print("utilization of Outfitting : {}".format(Monitor2.u))
    print("utilization of Painting : {}".format(Monitor3.u))

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

        ax[0][0].set_title("Arrival_rate/Troughput - {0}".format(Monitor1.port.name))
        ax[1][0].set_title("Arrival_rate/Troughput - {0}".format(Monitor2.port.name))
        ax[2][0].set_title("Arrival_rate/Troughput - {0}".format(Monitor3.port.name))

        plt.legend()
        plt.tight_layout()
        plt.show()

        if save_graph:
            fig.savefig(save_path + '/ArrivalRate_Troughput.png')

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