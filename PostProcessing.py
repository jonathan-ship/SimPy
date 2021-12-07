import numpy as np
import pandas as pd
import datetime
import random
import matplotlib.pyplot as plt
import plotly.figure_factory as ff


def graph(x, y, title=None, display=False, save=False, filepath=None):
    fig, ax = plt.subplots()
    ax.plot(x, y)
    ax.set_title(title)
    if display:
        plt.show()
    if save:
        fig.savefig(filepath + "/" + title + ".png")
        plt.close("all")


def cal_utilization(log, name=None, type=None, num=1, start_time=0.0, finish_time=0.0, step=None, display=False, save=False, filepath=None):
    log = log[(log[type] == name) & ((log["Event"] == "work_start") | (log["Event"] == "work_finish"))]

    if step:
        iteration = step
    else:
        iteration = 1

    time = np.linspace(start_time, finish_time, num=iteration)
    utilization = np.array([0.0 for _ in range(iteration)])
    idle_time = np.array([0.0 for _ in range(iteration)])
    working_time = np.array([0.0 for _ in range(iteration)])

    for i in range(iteration):
        if step and (i == iteration - 1):
            break
        if step:
            finish_time = time[i + 1]
        data = log[(log["Time"] >= start_time) & (log["Time"] <= finish_time)]

        total_time = 0.0
        for j in range(num):
            if type == "Process":
                name_of_subprocess = name + "_{0}".format(j)
            else:
                name_of_subprocess = name

            group = data[data["SubProcess"] == name_of_subprocess]
            work_start = group[group['Event'] == "work_start"]
            work_finish = group[group['Event'] == "work_finish"]

            if len(work_start) == 0 and len(work_finish) == 0:
                temp = log[log["SubProcess"] == name]
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
            working_time[i] += np.sum(work_finish - work_start)
            total_time += (finish_time - start_time)

        idle_time[i] = total_time - working_time[i]
        utilization[i] = working_time[i] / total_time if total_time != 0.0 else 0.0

    if step:
        utilization = pd.DataFrame({"Time": time[1:], "Utilization": utilization[:-1]})
        idle_time = pd.DataFrame({"Time": time[1:], "Idle_time": idle_time[:-1]})
        working_time = pd.DataFrame({"Time": time[1:], "Working_time": working_time[:-1]})
        if display or save:
            title = "utilization of {0} in ({1:.2f}, {2:.2f})".format(name, start_time, finish_time)
            graph(utilization["Time"], utilization["Utilization"], title=title, display=display, save=save, filepath=filepath)
        return utilization, idle_time, working_time
    else:
        return utilization[0], idle_time[0], working_time[0]


def cal_leadtime(log, name=None, type=None, mode="m", start_time=0.0, finish_time=0.0):
    event = {"m": ("part_created", "completed"),
             "p": ("Process_entered", "part_transferred_to_next_process", "part_transferred_to_next_process_with_tp", "part_transferred_to_Sink")}

    if not mode == "m":
        log = log[log[type] == name]

    leadtime_start = log[log["Event"] == event[mode][0]]
    if mode == "p":
        leadtime_finish = log[(log["Event"] == event[mode][1]) | (log["Event"] == event[mode][2]) | (log["Event"] == event[mode][3])]
    else:
        leadtime_finish = log[log["Event"] == event[mode][1]]

    idx = (leadtime_finish["Time"] >= start_time) & (leadtime_finish["Time"] <= finish_time)

    if len(idx[idx]) == 0:
        return 0.0

    leadtime_start = leadtime_start[:len(leadtime_finish)]
    leadtime_start = leadtime_start[list(idx)].sort_values(["Part"])
    leadtime_finish = leadtime_finish[list(idx)].sort_values(["Part"])
    leadtime_start = leadtime_start["Time"].reset_index(drop=True)
    leadtime_finish = leadtime_finish["Time"].reset_index(drop=True)

    lead_time_list = leadtime_finish - leadtime_start
    lead_time = np.mean(lead_time_list)

    return lead_time


def cal_throughput(log, name, type, mode='m', start_time=0.0, finish_time=0.0, step=None, display=False, save=False, filepath=None):
    if mode == 'm':
        log = log[(log[type] == name) & (log["Event"] == "part_transferred_to_Sink")]
    else:
        log = log[(log[type] == name) & ((log["Event"] == "part_transferred_to_next_process")
                                         |(log["Event"] == "part_transferred_to_next_process_with_tp")
                                         |(log["Event"] == "part_transferred_to_Sink"))]
    if step:
        iteration = step
    else:
        iteration = 1

    time = np.linspace(start_time, finish_time, num=iteration)
    throughput = np.array([0.0 for _ in range(iteration)])

    for i in range(iteration):
        if step and (i == iteration - 1):
            break
        if step:
            finish_time = time[i + 1]

        total_time = finish_time - start_time
        part_transferred = log[(log["Time"] >= start_time) & (log["Time"] <= finish_time)]
        throughput[i] = len(part_transferred) / total_time if total_time != 0.0 else 0.0

    if step:
        throughput = pd.DataFrame({"Time": time[1:], "Throughput": throughput[:-1]})
        if display or save:
            title = "throughput of {0} in ({1:.2f}, {2:.2f})".format(name, start_time, finish_time)
            graph(throughput["Time"], throughput["Throughput"], title=title, display=display, save=save, filepath=filepath)
        return throughput
    else:
        return throughput[0]


def cal_wip(log, mode="entire", process_name=None, start_time=None, finish_time=None):
    if start_time is None:
        start_time = log["Time"].min()
    if finish_time is None:
        finish_time = log["Time"].max()
    log = log[(log["Time"] >= start_time) & (log["Time"] <= finish_time)]
    if mode == "entire":
        event_log = log[(log['Event'] == "part_created") | (log['Event'] == "completed")]
    else:
        event_log = log[(log['Event'] == "Process_entered") | (log["Event"] == "work_start")]
        event_log = event_log[event_log["Process"] == process_name]

    part_list = list(np.unique(list(event_log["Part"])))
    event_grp = event_log.groupby(event_log["Part"])

    hanging_time = 0
    for part in part_list:
        each_part = event_grp.get_group(part)
        time_list = list(each_part["Time"])
        if len(time_list) == 2:  # Start ~ Finish 사이에 입고부터 출고까지 이루어진 경우
            hanging_time += time_list[1] - time_list[0]
        elif len(time_list) == 1:  # Start ~ Finish 사이에 입고만 된 경우 -> 아직 출고 전
            hanging_time += finish_time - time_list[0]

    wip = hanging_time / (finish_time - start_time)

    return wip

    # event = {"m": ("part_created", "completed"),
    #          "p": ("Process_entered", "part_transferred_to_next_process", "part_transferred_to_next_process_with_tp", "part_transferred_to_Sink"),
    #          "q": ("Process_entered", "work_start")}
    #
    # if not mode == "m":
    #     log = log[log[type] == name]
    # if mode == "p":
    #     log = log[(log["Event"] == event[mode][0]) | (log["Event"] == event[mode][1])
    #               | (log["Event"] == event[mode][2]) | (log["Event"] == event[mode][3])]
    # else:
    #     log = log[(log["Event"] == event[mode][0]) | (log["Event"] == event[mode][1])]
    #
    # if step:
    #     iteration = step
    # else:
    #     iteration = 1
    #
    # time = np.linspace(start_time, finish_time, num=iteration)
    # wip = np.array([0.0 for _ in range(iteration)])
    # duration = np.array([0.0 for _ in range(iteration)])
    #
    # for i in range(iteration):
    #     if step and (i == iteration - 1):
    #         break
    #     if step:
    #         finish_time = time[i + 1]
    #     data = log[(log["Time"] >= start_time) & (log["Time"] <= finish_time)]
    #
    #     total_time = finish_time - start_time
    #     data_by_group = data.groupby(data["Process"])
    #     for j, group in data_by_group:
    #         wip_start = group[group["Event"] == event[mode][0]]
    #         if not mode == "p":
    #             wip_finish = group[group["Event"] == event[mode][1]]
    #         else:
    #             wip_finish = group[(group["Event"] == event[mode][1]) | (group["Event"] == event[mode][2]) | (group["Event"] == event[mode][3])]
    #         if len(wip_start) == 0 and len(wip_finish) == 0:
    #             temp = log[log["Process"] == j]
    #             if len(temp) != 0:
    #                 idx = temp["Time"] >= start_time
    #                 if temp[idx].iloc[0]["Event"] == event[mode][1]:
    #                     duration += (finish_time - start_time)
    #             continue
    #         elif len(wip_start) != 0 and len(wip_finish) == 0:
    #             row = dict(wip_start.iloc[0])
    #             row["Time"] = finish_time
    #             row["Event"] = event[mode][1]
    #             wip_finish = pd.DataFrame([row])
    #         elif len(wip_start) == 0 and len(wip_finish) != 0:
    #             row = dict(wip_finish.iloc[0])
    #             row["Time"] = start_time
    #             row["Event"] = event[mode][0]
    #             wip_start = pd.DataFrame([row])
    #         else:
    #             if wip_start.iloc[0]["Part"] != wip_finish.iloc[0]["Part"]:
    #                 row = dict(wip_finish.iloc[0])
    #                 row["Time"] = start_time
    #                 row["Event"] = event[mode][0]
    #                 wip_start = pd.DataFrame([row]).append(wip_start)
    #             if wip_start.iloc[-1]["Part"] != wip_finish.iloc[-1]["Part"]:
    #                 row = dict(wip_start.iloc[-1])
    #                 row["Time"] = finish_time
    #                 row["Event"] = event[mode][1]
    #                 wip_finish = wip_finish.append(pd.DataFrame([row]))
    #
    #         wip_start = wip_start["Time"].reset_index(drop=True)
    #         wip_finish = wip_finish["Time"].reset_index(drop=True)
    #         duration[i] += np.sum(wip_finish - wip_start)
    #
    #     wip[i] = duration[i] / total_time if total_time != 0.0 else 0.0
    #
    # if step:
    #     wip = pd.DataFrame({"Time": time[1:], "WIP": wip[:-1]})
    #     if display or save:
    #         title = "WIP of {0} in ({1:.2f}, {2:.2f})".format(name, start_time, finish_time)
    #         graph(wip["Time"], wip["WIP"], title=title, display=display, save=save, filepath=filepath)
    #     return wip
    # else:
    #     return wip[0]


def gantt(data, process_list):
    list_part = list(data["Part"][data["Event"] == "part_created"])
    start = datetime.date(2020,8,31)
    r = lambda: random.randint(0, 255)
    dataframe = []
    # print('#%02X%02X%02X' % (r(),r(),r()))
    colors = ['#%02X%02X%02X' % (r(), r(), r())]

    for part in list_part:
        part_data = data[data["Part"] == part]
        #data_by_group = part_data.groupby(part_data["Process"])
        for i in process_list:
            group = part_data[part_data["Process"] == i]
            if (i != "Sink") and (i != "Source") and len(group) != 0:
                work_start = group[group["Event"] == "work_start"]
                work_start = list(work_start["Time"].reset_index(drop=True))
                work_finish = group[group["Event"] == "work_finish"]
                work_finish = list(work_finish["Time"].reset_index(drop=True))
                dataframe.append(dict(Task=i, Start=(start + datetime.timedelta(days=work_start[0])).isoformat(),Finish=(start + datetime.timedelta(days=work_finish[0])).isoformat(), Resource=part))
                colors.append('#%02X%02X%02X' % (r(), r(), r()))
            else:
                pass

    fig = ff.create_gantt(dataframe, colors=colors, index_col='Resource', group_tasks=True)
    fig.show()