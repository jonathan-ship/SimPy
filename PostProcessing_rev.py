import pandas as pd
import numpy as np


class Utilization(object):
    def __init__(self, data, process_dict, process):
        self.data = data
        self.process_dict = process_dict
        self.process = process  # utilization을 계산할 Process 혹은 Server
        self.type = "Process" if process in process_dict.keys() else "Server"

        # 공정에 관한 event 중 work_start인 event의 시간 저장 (총 시간 계산, working time 시간 계산 시 사용)
        # 공정에 관한 event 중 part_transferred인 event의 시간 저장 (총 시간 계산)
        # 공정에 관한 event 중 work_finish인 event의 시간 저장 (working time 시간 계산 시 사용)

    def utilization(self):
        idx = self.data["PROCESS"].map(lambda x: self.process in x)
        self.data = self.data.rename(index=idx)
        if True not in self.data.index:
            return 0
        self.data = self.data.loc[True, :]
        work_start = self.data["TIME"][self.data["EVENT"] == "work_start"]
        part_transferred = self.data["TIME"][self.data["EVENT"] == "part_transferred"]
        work_finish = self.data["TIME"][self.data["EVENT"] == "work_finish"]

        work_start = work_start.reset_index(drop=True)
        part_transferred = part_transferred.reset_index(drop=True)
        work_finish = work_finish.reset_index(drop=True)

        if len(work_start) * len(part_transferred) * len(work_finish) == 0:
            return 0  # utilization == 0

        # 총 가동 시간
        server_num = self.process_dict[self.process].server_num if self.type == "Process" else 1
        total_time = (part_transferred[len(part_transferred) - 1] - work_start[0]) * server_num

        # 총 작업 시간
        df_working = work_finish - work_start
        total_working = np.sum(df_working)

        # 가동률
        u = total_working / total_time
        return u


class LeadTime(object):
    def __init__(self, data):
        self.data = data  # Event Tracer
        self.list_LT = []
        self.part_list = list(data["PART"][(data["EVENT"] == "part_created") & (data["PROCESS"] == "Source")])

    def avg_LT(self):
        for part in self.part_list:
            part_data = self.data[self.data["PART"] == part]
            df_part_start = part_data["TIME"][part_data["EVENT"] == "part_created"]
            df_part_finish = part_data["TIME"][part_data["EVENT"] == "completed"]

            df_part_start = df_part_start.reset_index(drop=True)
            df_part_finish = df_part_finish.reset_index(drop=True)

            self.list_LT.append(df_part_finish[len(df_part_finish)-1] - df_part_start[0])

        return np.mean(self.list_LT)



