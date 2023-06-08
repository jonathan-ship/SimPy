#!/usr/bin/env python
# coding: utf-8

# In[9]:


import simpy
import numpy as np
import pandas as pd

np.random.seed(0)

IAT_MEAN = 3
PROCESS_1_MEAN = 2
PROCESS_1_STD_DEV = 1
PROCESS_2_MEAN = 1
PROCESS_2_STD_DEV = 1.5

log = []

class Task:
    def __init__(self, name, env, process1, process2):
        self.name = name
        self.env = env
        self.process1 = process1
        self.process2 = process2
        self.action = env.process(self.run())

    def run(self):
        arrival_time = self.env.now

        req = self.process1.request()
        yield req
        start_time_p1 = self.env.now
        process_time = max(np.random.normal(PROCESS_1_MEAN, PROCESS_1_STD_DEV), 0)
        yield self.env.timeout(process_time)
        finish_time_p1 = self.env.now
        self.process1.release(req)
        log.append({"task": self.name, "process": "Process_1", "arrival_time": arrival_time, "start_time": start_time_p1, "finish_time": finish_time_p1})

        req = self.process2.request()
        yield req
        start_time_p2 = self.env.now
        process_time = max(np.random.normal(PROCESS_2_MEAN, PROCESS_2_STD_DEV), 0)
        yield self.env.timeout(process_time)
        finish_time_p2 = self.env.now
        self.process2.release(req)
        log.append({"task": self.name, "process": "Process_2", "arrival_time": finish_time_p1, "start_time": start_time_p2, "finish_time": finish_time_p2})

def task_generator(env, process1, process2):
    task_number = 0
    while True:
        yield env.timeout(np.random.exponential(IAT_MEAN))
        task_number += 1
        Task(f"Task_{task_number}", env, process1, process2)

def run_simulation(run_time):
    env = simpy.Environment()
    process1 = simpy.Resource(env, capacity=1)
    process2 = simpy.Resource(env, capacity=1)
    env.process(task_generator(env, process1, process2))
    env.run(until=run_time)

def calculate_average_cycle_time(log_df):
    log_df["cycle_time"] = log_df["finish_time"] - log_df["arrival_time"]
    return log_df["cycle_time"].mean()

run_simulation(1000)
log_df = pd.DataFrame(log)
average_cycle_time = calculate_average_cycle_time(log_df)
print(f"평균 사이클 타임: {average_cycle_time} 분")


# In[ ]:




