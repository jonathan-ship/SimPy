import simpy
import time
import os
import scipy.stats as st
import numpy as np
import pandas as pd

from SimComponents import Sink, Process, Source
from Postprocessing import Utilization, ArrivalRateAndThroughput, Queue

if __name__ == "__main__":
    start_0 = time.time()

    #data pre-processing
    blocks = 18000
    blocks_1 = blocks + 1000  # 1000 = 음수 처리를 위한 여유분
    df_part = pd.DataFrame([i for i in range(blocks)], columns=["part"])

    columns = pd.MultiIndex.from_product([[i for i in range(4)], ['start_time', 'process_time', 'process']])
    data = pd.DataFrame([], columns=columns)

    ## process 1 : Assembly
    data[(0, 'start_time')] = np.floor(st.chi2.rvs(df=1.53, loc=-0, scale=0.22, size=blocks))
    data[(0, 'start_time')] = data[(0, 'start_time')].cumsum()
    temp = np.round(st.exponnorm.rvs(K=7.71, loc=2.40, scale=1.70, size=blocks_1))
    data[(0, 'process_time')] = temp[temp > 0][:blocks]
    data[(0, 'process')] = 'Assembly'

    ## process 2 : Outfitting
    data[(1, 'start_time')] = 0
    temp_2 = np.round(st.chi2.rvs(df=1.63, loc=1.00, scale=7.43, size=blocks_1))
    data[(1, 'process_time')] = temp_2[temp_2 > 0][:blocks]
    data[(1, 'process')] = 'Outfitting'

    ## process 3 : Painting
    data[(2, 'start_time')] = 0
    temp_3 = np.round(st.exponnorm.rvs(K=1.75, loc=8.53, scale=2.63, size=blocks_1))
    data[(2, 'process_time')] = temp_3[temp_3 > 0][:blocks]
    data[(2, 'process')] = 'Painting'

    ## Sink
    data[(3, 'start_time')] = None
    data[(3, 'process_time')] = None
    data[(3, 'process')] = 'Sink'

    data = pd.concat([df_part, data], axis=1)

    # Modeling
    env = simpy.Environment()

    ##
    event_tracer = {"event": [], "time": [], "part": [], "process": []}
    process_list = ['Assembly', 'Outfitting', 'Painting']
    process_dict = {}
    process = []

    # 작업장 수
    m_assy = 295
    m_oft = 285
    m_pnt = 232
    m_dict = {'Assembly': m_assy, 'Outfitting': m_oft, 'Painting': m_pnt}

    # Source, Sink modeling
    Source = Source(env, 'Source', data, process_dict, len(data), event_tracer=event_tracer, data_type="df")
    Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)
    # Process modeling
    for i in range(len(process_list)):
        process.append(Process(env, process_list[i], m_dict[process_list[i]], process_dict, event_tracer=event_tracer,
                               qlimit=10000))
    for i in range(len(process_list)):
        process_dict[process_list[i]] = process[i]
    process_dict['Sink'] = Sink

    # Run it
    start = time.time()
    env.run()
    finish = time.time()

    print('#' * 80)
    print("Results of simulation")
    print('#' * 80)

    # 코드 실행 시간
    print("data pre-processing : ", start - start_0)
    print("simulation execution time :", finish - start)
    print("total time : ", finish - start_0)

    # 총 리드타임 - 마지막 part가 Sink에 도달하는 시간
    print("Total Lead Time :", Sink.last_arrival)

    # save data
    save_path = './result'
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # event tracer dataframe으로 변환
    df_event_tracer = pd.DataFrame(event_tracer)
    df_event_tracer.to_excel(save_path + '/event_block_transfer_fitting.xlsx')

    # DATA POST-PROCESSING
    # Event Tracer을 이용한 후처리
    print('#' * 80)
    print("Data Post-Processing")
    print('#' * 80)

    # 가동율
    Utilization = Utilization(df_event_tracer, process_dict, process_list)
    Utilization.utilization()
    utilization = Utilization.u_dict

    for process in process_list:
        print("utilization of {} : ".format(process), utilization[process])

    # Arrival rate, Throughput
    ArrivalRateAndThroughput = ArrivalRateAndThroughput(df_event_tracer, process_list)
    ArrivalRateAndThroughput.arrival_rate()
    ArrivalRateAndThroughput.throughput()
    arrival_rate = ArrivalRateAndThroughput.process_arrival_rate
    throughput = ArrivalRateAndThroughput.process_throughput

    print('#' * 80)
    print("Arrival rate : ", arrival_rate)
    print("Throughput : ", throughput)

    # process 별 평균 대기시간, 총 대기시간
    Queue = Queue(df_event_tracer, process_list)
    Queue.waiting_time()
    print('#' * 80)
    for process in process_list:
        print("average waiting time of {} : ".format(process), Queue.average_waiting_time_dict[process])
    for process in process_list:
        print("total waiting time of {} : ".format(process), Queue.total_waiting_time_dict[process])

    # # throughput and arrival_rate
    # if Throughput_graph:
    #     smoothing = 1000
    #     throughput_assy = pd.Series(Monitor1.throughput).rolling(window=smoothing, min_periods=1).mean()
    #     throughput_oft = pd.Series(Monitor2.throughput).rolling(window=smoothing, min_periods=1).mean()
    #     throughput_pnt = pd.Series(Monitor3.throughput).rolling(window=smoothing, min_periods=1).mean()
    #     arrival_rate_assy = pd.Series(Monitor1.arrival_rate).rolling(window=smoothing, min_periods=1).mean()
    #     arrival_rate_oft = pd.Series(Monitor2.arrival_rate).rolling(window=smoothing, min_periods=1).mean()
    #     arrival_rate_pnt = pd.Series(Monitor3.arrival_rate).rolling(window=smoothing, min_periods=1).mean()
    #
    #     fig, ax = plt.subplots(3, 1, squeeze=False)
    #
    #     ax[0][0].plot(Monitor1.time, arrival_rate_assy, label='arrival_rate')
    #     ax[0][0].plot(Monitor1.time, throughput_assy, label='throughput')
    #     ax[1][0].plot(Monitor2.time, arrival_rate_oft, label='arrival_rate')
    #     ax[1][0].plot(Monitor2.time, throughput_oft, label='throughput')
    #     ax[2][0].plot(Monitor3.time, arrival_rate_pnt, label='arrival_rate')
    #     ax[2][0].plot(Monitor3.time, throughput_pnt, label='throughput')
    #
    #     ax[0][0].set_xlabel('time[day]')
    #     ax[0][0].set_ylabel('rate[EA/day]')
    #     ax[1][0].set_xlabel('time[day]')
    #     ax[1][0].set_ylabel('rate[EA/day]')
    #     ax[2][0].set_xlabel('time[day]')
    #     ax[2][0].set_ylabel('rate[EA/day]')
    #
    #     ax[0][0].set_title("Arrival_rate/Throughput - {0}".format(Monitor1.port.name))
    #     ax[1][0].set_title("Arrival_rate/Throughput - {0}".format(Monitor2.port.name))
    #     ax[2][0].set_title("Arrival_rate/Throughput - {0}".format(Monitor3.port.name))
    #
    #     plt.legend()
    #     plt.tight_layout()
    #     plt.show()
    #
    #     if save_graph:
    #         fig.savefig(save_path + '/ArrivalRate_Throughput.png')
    #
    # # WIP and m
    # if WIP_graph:
    #     fig, ax = plt.subplots(3, 1, squeeze=False)
    #
    #     ax[0][0].plot(Monitor1.time, Monitor1.WIP, label='WIP')
    #     ax[0][0].plot(Monitor1.time, Monitor1.M, label='m')
    #     ax[1][0].plot(Monitor2.time, Monitor2.WIP, label='WIP')
    #     ax[1][0].plot(Monitor2.time, Monitor2.M, label='m')
    #     ax[2][0].plot(Monitor3.time, Monitor3.WIP, label='WIP')
    #     ax[2][0].plot(Monitor3.time, Monitor3.M, label='m')
    #
    #     ax[0][0].set_xlabel('time[day]')
    #     ax[0][0].set_ylabel('num')
    #     ax[1][0].set_xlabel('time[day]')
    #     ax[1][0].set_ylabel('num')
    #     ax[2][0].set_xlabel('time[day]')
    #     ax[2][0].set_ylabel('num')
    #
    #     ax[0][0].set_title("WIP/m - {0}".format(Monitor1.port.name))
    #     ax[1][0].set_title("WIP/m - {0}".format(Monitor2.port.name))
    #     ax[2][0].set_title("WIP/m - {0}".format(Monitor3.port.name))
    #
    #     plt.legend()
    #     plt.tight_layout()
    #     plt.show()
    #
    #     if save_graph:
    #         fig.savefig(save_path + '/WIP_m.png')