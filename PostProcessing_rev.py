import pandas as pd
import numpy as np


class Utilization(object):
    def __init__(self, data, process_dict, process, type=None):
        self.data = data
        self.process_dict = process_dict
        self.type = type  # Process or Server
        self.process = process  # utilization을 계산할 Process 혹은 Server

    def utilization(self):
        # 공정에 관한 event 중 work_start인 event의 시간 저장 (총 시간 계산, working time 시간 계산 시 사용)
        # 공정에 관한 event 중 part_transferred인 event의 시간 저장 (총 시간 계산)
        # 공정에 관한 event 중 work_finish인 event의 시간 저장 (working time 시간 계산 시 사용)

        if self.type == "Process":  # type = Process 인 경우
            work_start = self.data["TIME"][
                (self.data["PROCESS"] == self.process) & (self.data["EVENT"] == "work_start")]
            part_transferred = self.data["TIME"][
                (self.data["PROCESS"] == self.process) & (self.data["EVENT"] == "part_transferred")]
            work_finish = self.data["TIME"][
                (self.data["PROCESS"] == self.process) & (self.data["EVENT"] == "work_finish")]
        else:  # type = server인 경우
            work_start = self.data["TIME"][
                (self.data["SERVER_ID"] == self.process) & (self.data["EVENT"] == "work_start")]
            part_transferred = self.data["TIME"][
                (self.data["SERVER_ID"] == self.process) & (self.data["EVENT"] == "part_transferred")]
            work_finish = self.data["TIME"][
                (self.data["SERVER_ID"] == self.process) & (self.data["EVENT"] == "work_finish")]

        work_start = work_start.reset_index(drop=True)
        part_transferred = part_transferred.reset_index(drop=True)
        work_finish = work_finish.reset_index(drop=True)

        # 총 가동 시간
        server_num = self.process_dict[self.process].server_num if self.type == "Process" else 1
        total_time = (part_transferred[len(part_transferred) - 1] - work_start[0]) * server_num

        # 총 작업 시간
        df_working = work_finish - work_start
        total_working = np.sum(df_working)

        # 가동률
        u = total_working / total_time
        return u



