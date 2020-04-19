import pandas as pd
import numpy as np
import scipy.stats as st
import simpy
import time

from SimComponents import Source, Sink, Process, EventTracer
from Postprocessing import Utilization, ArrivalRateAndThroughput


if __name__ == '__main__':

    start_0 = time.time()

    # csv 파일 pandas 객체 생성 // 000, 003, fin 중 선택 가능
    data_all = pd.read_csv('./data/PBS_assy_sequence_gen_fin.csv')
    data = data_all[["product", "plate_weld", "saw_front", "turn_over", "saw_back", "longi_weld", "unit_assy", "sub_assy"]]

    # process list
    process_list = ["plate_weld", "saw_front", "turn_over", "saw_back", "longi_weld", "unit_assy", "sub_assy"]

    # DATA PRE-PROCESSING
    df_part = pd.DataFrame(data["product"])
    df_part = df_part.rename(columns={"product": "part"})

    columns = pd.MultiIndex.from_product([[i for i in range(7)], ['start_time', 'process_time', 'process']])  # 7 = 공정 수 + Sink
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


    # SIMULATION
    env = simpy.Environment()

    process_dict = {}

    Source = Source(env, 'Source', df, process_dict, len(df), data_type="df")
    Sink = Sink(env, 'Sink', rec_lead_time=True, rec_arrivals=True)
    EventTracer = EventTracer()

    process = []
    m_dict = {}
    for i in range(len(process_list)):
        process.append(Process(env, process_list[i], 1, process_dict, 10000))

    for i in range(len(process_list)):
        process_dict[process_list[i]] = process[i]
        m_dict[process_list[i]] = 1

    process_dict['Sink'] = Sink
    process_dict['EventTracer'] = EventTracer

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
    print("Total Lead Time :", Sink.last_arrival, "\n")

    # DATA POST-PROCESSING
    # Event Tracer을 이용한 후처리
    part_list = list(data["product"])  # 후처리에 필요한 part name을 list에 저장
    df_event_tracer = process_dict['EventTracer'].event_tracer  # event log가 기록된 DataFrame
    df_event_tracer.to_excel('./data/event_PBS.xlsx')  # 엑셀로 출력

    print('#' * 80)
    print("Data Post-Processing")
    print('#' * 80)

    # 가동률
    Utilization = Utilization(df_event_tracer, m_dict, process_list)
    Utilization.utilization()
    utilization = Utilization.u_dict

    for process in process_list:
        print("utilization of {} : ".format(process), utilization[process])

    ArrivalRateAndThroughput = ArrivalRateAndThroughput(df_event_tracer, process_list)
    ArrivalRateAndThroughput.arrival_rate()
    ArrivalRateAndThroughput.throughput()
    arrival_rate = ArrivalRateAndThroughput.process_arrival_rate
    throughput = ArrivalRateAndThroughput.process_throughput

    print("Arrival rate : ", arrival_rate)
    print("Throughput : ", throughput)










