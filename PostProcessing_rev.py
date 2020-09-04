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


def graph(x, y, title=None, display=False, save=False):
    if display:
        plt.show()
    if save:
        plt.save()


def cal_utilization(log, name, type, num=1, start_time=0.0, finish_time=0.0, time_interval=0.1, display=False, save=False):
    if int((finish_time - start_time) / time_interval) <= 0:
        print("time interval is too wide")
        return pd.DataFrame()

    point = np.arange(start_time, finish_time, step=time_interval)
    time = np.array([0.0 for _ in range(len(point) - 1)])
    utilization = np.array([0.0 for _ in range(len(point) - 1)])
    idle_time = np.array([0.0 for _ in range(len(point) - 1)])
    working_time = np.array([0.0 for _ in range(len(point) - 1)])

    for i in range(len(point) - 1):
        time[i] = point[i + 1]
        utilization[i], idle_time[i], working_time[i] \
            = cal_utilization_avg(log, name, type, num=num, start_time=point[i], finish_time=point[i + 1])

    if display or save:
        graph(time, utilization, title="Utilization", display=display, save=save)
        graph(time, idle_time, title="Idle time", display=display, save=save)
        graph(time, working_time, title="Working time", display=display, save=save)

    result = pd.DataFrame({"Time": time, "Utilization": utilization, "Idle_time": idle_time, "Working_time": working_time})
    return result


def cal_utilization_avg(log, name, type, num=1, start_time=0.0, finish_time=0.0):
    total_time = 0.0
    utilization, idle_time, working_time = 0.0, 0.0, 0.0
    data_all = log[(log[type] == name) & ((log["Event"] == "work_start") | (log["Event"] == "work_finish"))]
    data = data_all[(data_all["Time"] >= start_time) & (data_all["Time"] <= finish_time)]

    for i in range(num):
        if type == "Process":
            group = data[data["SubProcess"] == (name + "_{0}".format(i))]
        else:
            group = data[data["SubProcess"] == name]

        work_start = group[group['Event'] == "work_start"]
        work_finish = group[group['Event'] == "work_finish"]

        if len(work_start) == 0 and len(work_finish) == 0:
            temp = data_all[data_all["SubProcess"] == i]
            if len(temp) != 0:
                idx = temp["Time"] >= start_time
                if temp[idx].iloc[0]["Event"] == "work_finsh":
                    working_time += (finish_time - start_time)
                    total_time += (finish_time - start_time)
                    continue
            working_time += 0.0
            total_time += (finish_time - start_time)
            continue
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
    utilization = working_time / total_time if total_time != 0.0 else 0.0

    return utilization, idle_time, working_time


def cal_leadtime(log, start_time=0.0, finish_time=0.0):
    part_created = log[log["Event"] == "part_created"]
    completed = log[log["Event"] == "completed"]

    idx = (completed["Time"] >= start_time) & (completed["Time"] <= finish_time)

    if len(idx[idx]) == 0:
        return 0.0

    part_created = part_created[:len(completed)]
    part_created = part_created[list(idx)].sort_values(["Part"])
    completed = completed[list(idx)].sort_values(["Part"])
    part_created = part_created["Time"].reset_index(drop=True)
    completed = completed["Time"].reset_index(drop=True)

    lead_time = completed - part_created
    lead_time = np.mean(lead_time)

    return lead_time


def cal_throughput(log, name, type, start_time=0.0, finish_time=0.0):
    throughput = 0.0
    part_transferred = log[(log[type] == name) & (log["Event"] == "part_transferred")]
    part_transferred = part_transferred[(part_transferred["Time"] >= start_time) & (part_transferred["Time"] <= finish_time)]
    if len(part_transferred) == 0:
        return throughput
    throughput = len(part_transferred) / (finish_time - start_time)
    #data = data[(data[type] == name) & ((data["Event"] == "queue_entered") | (data["Event"] == "part_transferred"))]
    #cycle_times = data["Time"].groupby(data["Part"]).diff().dropna()
    #throughput = 1 / np.mean(cycle_times)
    return throughput


def calculate_wip(log, start_time=0.0, finish_time=0.0, time_interval=0.1, display=False, save=False):
    if int((finish_time - start_time) / time_interval) <= 0:
        print("time interval is too wide")
        return pd.DataFrame()

    part_created = log[["Part", "Time"]][log["Event"] == "part_created"]
    completed = log[["Part", "Time"]][log["Event"] == "completed"]
    data = pd.merge(part_created, completed, on="Part", suffixes=["_start", "_finish"])

    time = np.arange(start_time, finish_time, step=time_interval)[1:]
    wip = np.array([0.0 for _ in range(len(time))])

    for i, row in data.iterrows():
        idx = np.where((time >= row["Time_start"]) and (time <= row["Time_finsih"]))
        wip[idx] += 1

    if display or save:
        graph(time, wip, title="WIP", display=display, save=save)

    result = pd.DataFrame({"Time": time, "WIP": wip})
    return result


def calculate_wip_avg(log, start_time=0.0, finish_time=0.0):
    part_created = log[log["Event"] == "part_created"]
    completed = log[log["Event"] == "completed"]
    part_created = part_created[(part_created["Time"] >= start_time) & (part_created["Time"] <= finish_time)]
    completed = completed[(completed["Time"] >= start_time) & (completed["Time"] <= finish_time)]



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
        for i in range(len(process_list)):
            part_data = data[data["Part"] == part]
            part_start = list((part_data["Time"][(part_data["Event"] == "work_start") | (part_data["Event"] == "part_created")]).reset_index(drop=True))
            part_finish = list((part_data["Time"][(part_data["Event"] == "work_finish") | (part_data["Event"] == "part_transferred") & (part_data["Process"] == "Source")]).reset_index(drop=True))
            if len(part_start) != (len(process_list) + 1):
                if part_data["Time"][(part_data["Event"] == "work_start") & (part_data["Process"] == process_list[i])] not in part_start:
                    part_start.insert(i+1, part_data["Time"]["Event"] == "part_transferred" & part_data["Process"] == process_list[i-1])
                    part_finish.insert(i+1, part_data["Time"]["Event"] == "work_finish" & part_data["Process"] == process_list[i+1])

            dataframe.append(dict(Task=process_list[i], Start=(start + datetime.timedelta(days=part_start[i+1])).isoformat(), Finish=(start + datetime.timedelta(days=part_finish[i+1])).isoformat(),Resource=part))
            colors.append('#%02X%02X%02X' % (r(), r(), r()))

    fig = ff.create_gantt(dataframe, colors=colors, index_col='Resource', group_tasks=True)
    fig.show()
