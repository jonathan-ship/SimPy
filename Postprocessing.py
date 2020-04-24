import numpy as np
import pandas as pd


class Utilization(object):

    def __init__(self, data, process_dict, process_list):
        self.data = data  # event tracer data
        self.process_dict = process_dict  # 모델링 된 Process 객체가 저장된 dictionary
        self.process_list = process_list  # 공정 이름이 저장된 list
        self.u_dict = {}  # 공정 별 utilization을 저장 할 dictionary

    def utilization(self):
        for process in self.process_list:  # process 마다 utilization 계산
            # 공정에 관한 event 중 work_start인 event의 시간 저장 (총 시간 계산, working time 시간 계산 시 사용)
            work_start = self.data["time"][(self.data["process"] == process) & (self.data["event"] == "work_start")]
            work_start = work_start.reset_index(drop=True)

            # 공정에 관한 event 중 part_transferred인 event의 시간 저장 (총 시간 계산)
            part_transferred = self.data["time"][
                (self.data["process"] == process) & (self.data["event"] == "part_transferred")]
            part_transferred = part_transferred.reset_index(drop=True)

            # 공정에 관한 event 중 work_finish인 event의 시간 저장 (working time 시간 계산 시 사용)
            work_finish = self.data["time"][(self.data["process"] == process) & (self.data["event"] == "work_finish")]
            work_finish = work_finish.reset_index(drop=True)

            # 총 가동 시간
            total_time = (part_transferred[len(part_transferred) - 1] - work_start[0]) * (self.process_dict[process].server_num)

            # 총 작업 시간
            df_working = work_finish - work_start
            total_working = np.sum(df_working)

            # 가동률
            self.u_dict[process] = total_working / total_time


class ArrivalRateAndThroughput(object):
### 수정 요망 - 시간에 따른 공정 별 arrival rate / throughput 계산
    def __init__(self, data, process_list):
        self.data = data
        self.process_list = process_list
        self.process_arrival_rate = 0.0
        self.process_throughput = 0.0

    def arrival_rate(self):
        df_arrival = self.data["time"][self.data["event"] == "part_created"]
        df_arrival = df_arrival.reset_index(drop=True)

        arrival_list = []
        for i in range(len(df_arrival) - 1):
            arrival_list.append(df_arrival.loc[i+1] - df_arrival.loc[i])

        self.process_arrival_rate = 1 / np.mean(arrival_list)

    def throughput(self):
        df_TH = self.data["time"][
            (self.data["event"] == "part_transferred") & (self.data["process"] == self.process_list[-1])]
        df_TH = df_TH.reset_index(drop=True)

        TH_list = []
        for i in range(len(df_TH) - 1):
            TH_list.append(df_TH.loc[i + 1] - df_TH.loc[i])

        self.process_throughput = 1 / np.mean(TH_list)


class Queue(object):

    def __init__(self, data, process_list):
        self.data = data
        self.process_list = process_list
        self.average_waiting_time_dict = {}
        self.total_waiting_time_dict = {}

    def waiting_time(self):
        for process in self.process_list:
            df_waiting_start = self.data["time"][
                (self.data["process"] == process) & (self.data["event"] == "queue_entered")]
            df_waiting_start = df_waiting_start.reset_index(drop=True)

            df_waiting_finish = self.data["time"][
                (self.data["process"] == process) & (self.data["event"] == "queue_released")]
            df_waiting_finish = df_waiting_finish.reset_index(drop=True)

            df_waiting_time = df_waiting_finish - df_waiting_start

            self.average_waiting_time_dict[process] = np.mean(df_waiting_time)
            self.total_waiting_time_dict[process] = np.sum(df_waiting_time)
