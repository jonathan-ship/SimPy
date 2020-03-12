import random
import pandas as pd
import functools
import simpy
from SimComponents import Source, Sink, Process, Monitor
import time

if __name__ == '__main__':
    # csv 파일 pandas 객체 생성
    data_all = pd.read_csv('./data/PBS_assy_sequence_gen_003.csv')

    data = data_all[["plate_weld","saw_front","turn_over", "saw_back", "longi_weld", "unit_assy", "sub_assy"]]
    data["start"] = 0

    data = data[["start" ,"plate_weld", "start", "saw_front", "start", "turn_over", "start", "saw_back", "start", "longi_weld",
                 "start", "unit_assy", "start", "sub_assy"]]

    columns = pd.MultiIndex.from_product([["plate_weld","saw_front","turn_over", "saw_back", "longi_weld", "unit_assy",
                                           "sub_assy"], ['start_time', 'process_time']])
    data.columns = columns


    random.seed(42)
    adist = functools.partial(random.randrange,3,7)
    # samp_dist = functools.partial(random.expovariate, 1)
    samp_dist = 1

    RUN_TIME = 500

    env = simpy.Environment()

    m = 1

    Source = Source(env, "Source", data)
    Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)
    plate_weld = Process(env, "plate_weld", m, qlimit=10000)
    saw_front = Process(env, "saw_front", m, qlimit=10000)
    turn_over = Process(env, "turn_over", m, qlimit=10000)
    saw_back = Process(env, "saw_back", m, qlimit=10000)
    longi_weld = Process(env, "longi_weld", m, qlimit=10000)
    unit_assy = Process(env, "unit_assy", m, qlimit=10000)
    sub_assy = Process(env, "sub_assy", m, qlimit=10000)

    Source.out = plate_weld
    plate_weld.out = saw_front
    saw_front.out = turn_over
    turn_over.out = saw_back
    saw_back.out = longi_weld
    longi_weld.out = unit_assy
    unit_assy.out = sub_assy
    sub_assy.out = Sink

    Monitor1 = Monitor(env, plate_weld, samp_dist)
    Monitor2 = Monitor(env, saw_front, samp_dist)
    Monitor3 = Monitor(env, turn_over, samp_dist)
    Monitor4 = Monitor(env, saw_back, samp_dist)
    Monitor5 = Monitor(env, longi_weld, samp_dist)
    Monitor6 = Monitor(env, unit_assy, samp_dist)
    Monitor7 = Monitor(env, sub_assy, samp_dist)

    # Run it
    start = time.time()
    env.run()
    finish = time.time()


    # 시작 시간 저장 (0.05초)
    # Run it
    env.run(until=RUN_TIME)
    print("time :", time.time() - start)

    # Anylogic에서 0.24초

    print('#'*80)
    print("Results of simulation")
    print('#'*80)

    print("Total Lead Time : ", Sink.last_arrival)

    print("utilization of plate weld : {}".format(Monitor1.u))
    print("utilization of saw front : {}".format(Monitor2.u))
    print("utilization of turn over : {}".format(Monitor3.u))
    print("utilization of saw back : {}".format(Monitor4.u))
    print("utilization of longi weld : {}".format(Monitor5.u))
    print("utilization of unit assy : {}".format(Monitor6.u))
    print("utilization of sub assy : {}".format(Monitor7.u))


    '''print("Total Lead Time : ", Sink.last_arrival) # 총 리드타임 - 마지막 part가 Sink에 도달하는 시간

    print("Sink: average lead time = {:.3f}".format(sum(Sink.waits)/len(Sink.waits))) # 모든 parts들의 리드타임의 평균
    #print("Lead time of Last 10 Parts: " + ", ".join(["{:.3f}".format(x) for x in Sink.waits[-10:]]))
    #print("Process1: Last 10 queue sizes: {}".format(Monitor1.sizes[-10:]))
    #print("Sink: Last 10 arrival times: " + ", ".join(["{:.3f}".format(x) for x in Sink.arrivals[-10:]])) # 모든 공정을 거친 assembly가 최종 노드에 도착하는 시간 간격 - TH 계산 가능

    ## 공정별 대기시간의 합
    names = ["Process1", "Process2", "Process3", "Process4", "Process5", "Process6", "Process7"]
    waiting_time = {}
    for name in names:
        t = 0
        for i in range(len(Sink.waiting_list)):
            t += Sink.waiting_list[i][name + " waiting finish"] - Sink.waiting_list[i][name + " waiting start"]
        waiting_time[name] = t

    plt.bar(range(len(waiting_time)), list(waiting_time.values()), align='center')
    plt.title("Histogram for waiting time")
    plt.xlabel("Process")
    plt.ylabel("Waiting time")
    plt.show()

    ## 공정별 가동
    processes = [Process1, Process2, Process3, Process4, Process5, Process6, Process7]
    utilization = {}
    for process in processes:
        utilization[process.name] =  getattr(process, "working_time")/Sink.last_arrival

    plt.bar(range(len(utilization)), list(utilization.values()), align='center')
    plt.title("Histogram for utilization")
    plt.xlabel("Process")
    plt.ylabel("utilization")
    plt.show()

    ## 공정별 평균 재공수률
    monitors = [Monitor1, Monitor2, Monitor3, Monitor4, Monitor5, Monitor6, Monitor7]
    WIP_avg = {}
    for monitor in monitors:
        WIP_avg[monitor.name] = sum(getattr(monitor, "sizes"))/len(getattr(monitor, "sizes"))

    plt.bar(range(len(WIP_avg)), list(WIP_avg.values()), align='center')
    plt.title("Histogram for WIP")
    plt.xlabel("Process")
    plt.ylabel("Average WIP")
    plt.show()'''

    """
    fig, axis = plt.subplots()
    axis.hist(Sink.waits, bins=100, density=True)
    axis.set_title("Histogram for waiting times")
    axis.set_xlabel("time")
    axis.set_ylabel("normalized frequency of occurrence")
    plt.show()
    fig, axis = plt.subplots()
    axis.hist(Sink.arrivals, bins=100, density=True)
    axis.set_title("Histogram for Sink Interarrival times")
    axis.set_xlabel("time")
    axis.set_ylabel("normalized frequency of occurrence")
    plt.show()
    fig, axis = plt.subplots()
    axis.hist(Monitor1.sizes, bins=10, density=True)
    axis.set_title("Histogram for Process1 WIP")
    axis.set_xlabel("time")
    axis.set_ylabel("normalized frequency of occurrence")
    plt.show()
"""