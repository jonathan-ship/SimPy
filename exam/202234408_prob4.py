#!/usr/bin/env python
# coding: utf-8

# In[3]:


import simpy
import numpy as np

SIM_TIME = 1_000_000
IAT_MEAN = 3
PROCESS_TIMES = [30, 50, 40]
CAPACITY_LIMIT = 0.9

def source(env, process):
    while True:
        yield env.timeout(np.random.exponential(IAT_MEAN))
        env.process(operation(env, process))

def operation(env, process):
    with process.request() as req:
        yield req
        yield env.timeout(np.random.exponential(PROCESS_TIMES[process_to_run]))

if __name__ == "__main__":
    for process_to_run, process_time in enumerate(PROCESS_TIMES):
        num_machines = int(SIM_TIME * CAPACITY_LIMIT / process_time)
        print(f"프로세스 {process_to_run + 1}을 위한 기계 수: {num_machines}")

        env = simpy.Environment()
        process = simpy.Resource(env, capacity=num_machines)
        env.process(source(env, process))
        env.run(until=SIM_TIME)

        utilization = process.count / num_machines
        print(f"프로세스 {process_to_run + 1}의 이용률: {utilization}\n")


# In[ ]:





# In[ ]:




