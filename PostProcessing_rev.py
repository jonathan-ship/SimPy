import numpy as np
import pandas as pd
import math as m
import gantt
import time
from datetime import timedelta
import datetime
import random
from matplotlib import pyplot as plt

import sys
sys.path.insert(0, 'c:\pyzo2015a\lib\site-packages\plotly')
import plotly.figure_factory as ff


def cal_utilization(data, name, type, start_time=0.0, finish_time=0.0):
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
            return utilization, idle_time, working_time
        elif len(work_start) != 0 and len(work_finish) == 0:
            row = dict(work_start.iloc[0])
            row["Time"] = finish_time
            row["Event"] = "work_finish"
            work_finish = pd.DataFrame([row])
        elif len(work_start) == 0 and len(work_finish) != 0:
            row = dict(work_finish.iloc[0])
            row["Time"] = start_time
            row["Event"] = "work_start"
            work_start = pd.DataFrame([row])
        else:
            if work_start.iloc[0]["Part"] != work_finish.iloc[0]["Part"]:
                row = dict(work_finish.iloc[0])
                row["Time"] = start_time
                row["Event"] = "work_start"
                work_start = pd.DataFrame([row]).append(work_start)
            if work_start.iloc[-1]["Part"] != work_finish.iloc[-1]["Part"]:
                row = dict(work_start.iloc[-1])
                row["Time"] = finish_time
                row["Event"] = "work_finish"
                work_finish = work_finish.append(pd.DataFrame([row]))
        work_start = work_start["Time"].reset_index(drop=True)
        work_finish = work_finish["Time"].reset_index(drop=True)

        working_time += np.sum(work_finish - work_start)
        total_time += (finish_time - start_time)
    idle_time = total_time - working_time
    utilization = working_time / total_time if total_time != 0 else 0

    return utilization, idle_time, working_time


def cal_leadtime(data, start_time=0.0, finish_time=0.0):
    part_created = data[data["Event"] == "part_created"]
    completed = data[data["Event"] == "completed"]
    part_created = part_created[:len(completed)]

    idx = (completed["Time"] >= start_time) & (completed["Time"] <= finish_time)
    part_created = part_created[list(idx)].sort_values(["Part"])
    completed = completed[list(idx)].sort_values(["Part"])
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


def wip(data, WIP_type=None, type =None, name=None):
    if WIP_type == "WIP_m":
        wip_start = data[data["Event"] == "part_created"]
        wip_finish = data[data["Event"] == "completed"]
    else:  # WIP_type = "WIP_p" / "WIP_q"
        data = data[data[type] == name]
        wip_start = data[data["Event"] == "queue_entered"]
        if WIP_type == "WIP_p":
            wip_finish = data[data["Event"] == "part_transferred"]
        else:  # WIP_type = "WIP_q":
            wip_finish = data[data["Event"] == "queue_released"]

    wip_start = wip_start.reset_index(drop=True)
    wip_finish = wip_finish.reset_index(drop=True)

    time_lange = wip_finish["Time"][len(wip_finish) - 1]
    wip_list = [0 for _ in range(m.ceil(time_lange) + 1)]

    wip_start.sort_index(inplace=True)
    wip_finish.sort_index(inplace=True)

    data_len = min(len(wip_start), len(wip_finish))
    wip_start = wip_start[:data_len]
    wip_finish = wip_finish[:data_len]

    wip_start = wip_start["Time"]
    wip_finish = wip_finish["Time"]

    for i in range(len(wip_start)):
        for j in range(m.ceil(wip_start[i]), m.ceil(wip_finish[i])):
            wip_list[j] += 1

    return wip_list

def gantt(data, process_list):
    list_part = list(data["Part"][data["Event"] == "part_created"])
    start = datetime.date(2020,8,31)
    r = lambda: random.randint(0, 255)
    dataframe = []
    # print('#%02X%02X%02X' % (r(),r(),r()))
    colors = ['#%02X%02X%02X' % (r(), r(), r())]

    for part in list_part:
        part_data = data[data["Part"] == part]
        part_start = list((part_data["Time"][(part_data["Event"] == "work_start") | (part_data["Event"] == "part_created")]).reset_index(drop=True))
        part_finish = list((part_data["Time"][(part_data["Event"] == "work_finish") | (part_data["Event"] == "part_transferred") & (part_data["Process"] == "Source")]).reset_index(drop=True))

        for i in range(len(process_list)-1):
            dataframe.append(dict(Task=process_list[i], Start=(start + datetime.timedelta(days=part_start[i+1])).isoformat(), Finish=(start + datetime.timedelta(days=part_finish[i+1])).isoformat(),Resource=part))
            colors.append('#%02X%02X%02X' % (r(), r(), r()))

    fig = ff.create_gantt(dataframe, colors=colors, index_col='Resource', group_tasks=True)
    fig.show()
