import numpy as np
import pandas as pd
import math as m


def cal_utilization(data, name, type, start_time=0.0, finish_time=0.0,):
    total_time = 0.0
    utilization, idle_time, working_time = 0.0, 0.0, 0.0
    data = data[(data[type] == name) & ((data["Event"] == "work_start") | (data["Event"] == "work_finish"))]
    data = data[(data["Time"] >= start_time) & (data["Time"] <= finish_time)]

    if len(data) == 0:
        return utilization, idle_time, working_time

    data_by_group = data.groupby(data['SubProcess'])
    for i, group in data_by_group:
        work_start = group[group['Event'] == "work_start"]
        work_finish = group[group['Event'] == "work_finish"]
        if len(work_start) == 0 and len(work_finish) == 0:
            pass
        elif len(work_start) != 0 and len(work_finish) == 0:
            row = work_start.iloc[0]
            row["Time"] = finish_time
            row["Event"] = "work_finish"
            work_finish = pd.DataFrame([row])
        elif len(work_start) == 0 and len(work_finish) != 0:
            row = work_finish.iloc[0]
            row["Time"] = start_time
            row["Event"] = "work_start"
            work_start = pd.DataFrame([row])
        else:
            if work_start.iloc[0]["Part"] != work_finish.iloc[0]["Part"]:
                row = work_finish.iloc[0]
                row["Time"] = start_time
                row["Event"] = "work_start"
                work_start = pd.DataFrame([row]).append(work_start)
            if work_start.iloc[-1]["Part"] != work_finish.iloc[-1]["Part"]:
                row = work_start.iloc[-1]
                row["Time"] = finish_time
                row["Event"] = "work_finish"
                work_finish = work_finish.append(pd.DataFrame([row]))
        work_start = work_start["Time"].reset_index(drop=True)
        work_finish = work_finish["Time"].reset_index(drop=True)
        working_time += np.sum(work_finish - work_start)
        total_time += (finish_time - start_time)
    idle_time = total_time - working_time
    utilization = working_time / total_time

    return utilization, idle_time, working_time


def cal_leadtime(data, start_time=0.0, finish_time=0.0):
    part_created = data[data["Event"] == "part_created"]
    completed = data[data["Event"] == "completed"]

    idx = (completed["Time"] >= start_time) & (completed["Time"] <= finish_time)
    part_created = part_created[idx.to_list()].sort_values(["Part"])
    completed = completed[idx.to_list()].sort_values(["Part"])
    part_created = part_created["Time"].reset_index(drop=True)
    completed = completed["Time"].reset_index(drop=True)

    lead_time = completed - part_created
    lead_time = np.mean(lead_time)

    return lead_time


def cal_throughput(data, name, type, start_time=0.0, finish_time=0.0):
    throughput = 0.0
    part_transferred = data[(data[type] == name) & (data["Event"] == "part_transferred")]
    part_transferred = part_transferred[(part_transferred["Time"] >= start_time) & (part_transferred["Time"] <= finish_time)]
    if len(part_transferred) == 0:
        return throughput
    throughput = len(part_transferred) / (finish_time - start_time)
    #data = data[(data[type] == name) & ((data["Event"] == "queue_entered") | (data["Event"] == "part_transferred"))]
    #cycle_times = data["Time"].groupby(data["Part"]).diff().dropna()
    #throughput = 1 / np.mean(cycle_times)
    return throughput


class WIP(object):
    def __init__(self, event_tracer, WIP_type=None, process=None):
        self.data = event_tracer
        # "WIP_m": model 전체의 WIP, "WIP_p": 특정 process의 WIP, "WIP_q": 특정 process의 WIP_q
        self.WIP_type = WIP_type
        self.process = process
        self.wip_list = None

    def wip_preprocessing(self):
        if self.WIP_type == "WIP_m":
            wip_start = self.data[self.data["EVENT"] == "part_created"]
            wip_finish = self.data[self.data["EVENT"] == "completed"]
        else:  # WIP_type = "WIP_p" / "WIP_q"
            idx = self.data["PROCESS"].map(lambda x: self.process in x)
            self.data = self.data.rename(index=idx)
            self.data = self.data.loc[True, :]
            wip_start = self.data[self.data["EVENT"] == "queue_entered"]
            if self.WIP_type == "WIP_p":
                wip_finish = self.data[self.data["EVENT"] == "part_transferred"]
            else:  # WIP_type = "WIP_q":
                wip_finish = self.data[self.data["EVENT"] == "queue_released"]

        wip_start = wip_start.reset_index(drop=True)
        wip_finish = wip_finish.reset_index(drop=True)

        time_lange = wip_finish["TIME"][len(wip_finish) - 1]
        wip_list = [0 for _ in range(m.ceil(time_lange) + 1)]

        wip_start.sort_values(by=["PART"], inplace=True)
        wip_finish.sort_values(by=["PART"], inplace=True)

        data_len = min(len(wip_start), len(wip_finish))
        wip_start = wip_start[:data_len]
        wip_finish = wip_finish[:data_len]

        return wip_list, wip_start, wip_finish

    def cal_wip(self):
        self.wip_list, wip_start, wip_finish = self.wip_preprocessing()
        wip_start = wip_start["TIME"]
        wip_finish = wip_finish["TIME"]

        for i in range(len(wip_start)):
            for j in range(m.ceil(wip_start[i]), m.ceil(wip_finish[i])):
                self.wip_list[j] += 1

        return self.wip_list

