import time
import simpy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from datetime import datetime
from SimComponents import Source, Sink, Process, Monitor
from PostProcessing import cal_utilization


def optimimze(process_list, data):

    # initialize the number of servers(sub-processes) and utilization
    server_num = np.full(len(process_list), 1)
    utilization = np.ones(len(process_list))

    # repeat the simulation and adjust the number of servers
    while np.any(utilization > 0.9):

        # modeling the source, process, and monitor
        env = simpy.Environment()
        model = {}
        monitor = Monitor('../result/event_log_master_plan.csv')
        source = Source(env, 'Source', data, model, monitor)
        for i in range(len(process_list) + 1):
            if i == len(process_list):
                model['Sink'] = Sink(env, 'Sink', monitor)
            else:
                model[process_list[i]] = Process(env, process_list[i], server_num[i], model, monitor)

        # run the simulation
        simulation_start = time.time()
        env.run()
        simulation_finish = time.time()
        print("simulation time: {0}".format(simulation_finish - simulation_start))
        monitor.save_event_tracer()

        # calculate the utilization
        log = pd.read_csv('../result/event_log_master_plan.csv')
        for i in range(len(process_list)):
            utilization[i], _, _ = cal_utilization(log, name=process_list[i], type="Process", num=server_num[i],
                                                   start_time=0.0, finish_time=model["Sink"].last_arrival)

        # if the utilization is higher than 0.9, increase the number of servers in the corresponding process
        idx_up = utilization > 0.9
        server_num[idx_up] += 1

    return server_num, utilization


if __name__ == "__main__":
    preprocessing_start = time.time()

    # import raw data
    raw_data = pd.read_excel("./data/master_planning.xlsx", engine="openpyxl")

    # select the columns containing essesntial information to run simulation
    data_selected = raw_data[["PROJECTNO", "LOCATIONCODE", "ACTIVITYCODE", "PLANSTARTDATE", "PLANDURATION"]]

    # set the block id(part id) as the project number + location code
    data_selected["BLOCKID"] = data_selected["PROJECTNO"] + data_selected["LOCATIONCODE"]

    # remove the abnormal activity codes
    data_selected = data_selected[data_selected["LOCATIONCODE"] != "OOO"]

    # remove the location code from the activity code
    data_selected["ACTIVITYCODE"] = data_selected.apply(lambda x: x["ACTIVITYCODE"][x["ACTIVITYCODE"].find(x["LOCATIONCODE"]) + len(x["LOCATIONCODE"]):].strip(), axis=1)

    # convert the planned start date of each activity to integer type
    data_selected["PLANSTARTDATE"] = pd.to_datetime(data_selected["PLANSTARTDATE"], format='%Y-%m-%d')
    data_selected = data_selected[data_selected["PLANSTARTDATE"] >= datetime(2018, 1, 1)]
    earliest_date = data_selected["PLANSTARTDATE"].min()
    data_selected["PLANSTARTDATE"] = (data_selected["PLANSTARTDATE"] - earliest_date).dt.days

    # set block id to data index
    data_selected = data_selected.set_index(["BLOCKID"])

    # group data by the same block
    data_group = data_selected[["PLANSTARTDATE", "PLANDURATION", "ACTIVITYCODE"]].groupby(level=0)

    # save the names of processes in the list
    process_list = list(data_selected["ACTIVITYCODE"].drop_duplicates())

    # generate a dataframe to store the planned data for each block in rows
    columns = pd.MultiIndex.from_product([[i for i in range(len(process_list) + 1)],
                                          ["start_time", "process_time", "process"]])
    data_processed = pd.DataFrame(columns=columns)

    # store activities for each block in a row of dataframe
    for i, block in data_group:
        block = block.rename(columns={"PLANSTARTDATE": "start_time", "PLANDURATION": "process_time", "ACTIVITYCODE": "process"})
        block = block.append(pd.DataFrame({"start_time": [None], "process_time": [None], "process": ["Sink"]}))
        block = block.sort_values(by=["start_time"]).reset_index(drop=True)
        data_processed.loc[i] = block.T.unstack()

    # sort the dataframe according to the start date of first activity of blocks
    data_processed = data_processed.sort_values(by=[(0, 'start_time')], axis=0)

    preprocessing_finish = time.time()
    print("preprocessing time: {0}".format(preprocessing_finish - preprocessing_start))

    # find the optimal number of sub-processes for each process
    server_num, utilization = optimimze(process_list, data_processed)

    # graph the results of optimization
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()
    bar = ax1.bar(process_list, server_num, color="orange", label="number of servers")
    line = ax2.plot(process_list, utilization * 100, color="cornflowerblue", label="utilization", marker="o")

    ax1.set_title("optimization results", fontsize=13, fontweight="bold")
    ax1.set_xlabel("activities")
    ax1.set_ylabel("number")
    ax2.set_ylabel("percent")

    ax2.set_ylim([0, 100])

    fig.autofmt_xdate(rotation=90, ha="center")
    fig.legend(loc=1, bbox_to_anchor=(1, 1), bbox_transform=ax1.transAxes)

    plt.show()
