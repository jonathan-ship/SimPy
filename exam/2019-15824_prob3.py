"""
Jiwon Baek
Topics in Ship Production Engineering Final Exam
Problem 3
"""


import simpy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


class Part:
    def __init__(self, id, enter_time):
        self.id = id
        self.enter_time = enter_time
        self.started_time = 0
        self.finished_time = 0


class Source:
    def __init__(self, env, model, name, mean_IAT):
        self.env = env
        self.model = model
        self.mean_IAT = mean_IAT
        self.name = name
        self.part_id = 0
        self.env.process(self.processing())
        self.create_log = []

    def processing(self):
        while True:
            self.part_id += 1
            part = Part(self.part_id, enter_time=self.env.now)
            self.create_log.append(self.env.now)
            self.model['process1'].store.put(part)
            IAT = np.random.exponential(self.mean_IAT)
            yield self.env.timeout(IAT)


class Sink:
    def __init__(self, env, model, name):
        self.env = env
        self.model = model
        self.name = name
        self.store = simpy.Store(env)
        self.env.process(self.processing())

        self.part_count = 0

    def processing(self):
        while True:
            part = yield self.store.get()
            self.part_count += 1


class Process:
    def __init__(self, env, model, name, mean_service_time, capacity, next_process_name):

        self.model = model
        self.name = name
        self.next_process_name = next_process_name
        self.total_working_time = 0.0
        self.service_time = 0.0
        self.mean_service_time = mean_service_time
        self.env = env
        self.store = simpy.Store(env)
        self.machines = simpy.Resource(env, capacity=capacity)
        self.env.process(self.processing())
        self.log_start = []
        self.log_finish = []

    def processing(self):
        while True:
            req = self.machines.request()
            yield req
            part = yield self.store.get()

            self.env.process(self.servicing(part, req, self.mean_service_time))
            self.total_working_time += self.service_time


    def servicing(self, part, req, mean_st):
        self.log_start.append(self.env.now)
        servicetime = np.random.exponential(mean_st)
        self.service_time = servicetime
        print(self.name, 'started processing part %d at %4.2f' % (part.id, self.env.now))
        part.started_time = self.env.now
        yield self.env.timeout(servicetime)
        print(self.name, 'finished processing part %d at %4.2f' % (part.id, self.env.now))
        part.finished_time = self.env.now
        self.log_finish.append(self.env.now)
        self.env.process(self.to_next_process(part, req, self.next_process_name))

    def to_next_process(self, part, req, next_process_name):
        yield self.model[next_process_name].store.put(part)
        self.machines.release(req)


np.random.seed(5)


finished_list = []

MEAN_IAT = 3
MEAN_P1 = 2
MEAN_P2 = 1
SIMTIME = 100

env = simpy.Environment()
model = {}
model['source'] = Source(env, model, 'source', MEAN_IAT)
model['process1'] = Process(env, model, 'process1', MEAN_P1, 1, 'process2')
model['process2'] = Process(env, model, 'process2', MEAN_P2, 1, 'sink')
model['sink'] = Sink(env, model, 'sink')
env.run(until=SIMTIME)

p1_finished_jobs = len(model['process1'].log_finish)
p2_finished_jobs = len(model['process2'].log_finish)
process1_ct = np.array(model['process1'].log_finish) - np.array(model['process1'].log_start[:p1_finished_jobs])
process1_ct_mean = np.mean(process1_ct)
process2_ct = np.array(model['process2'].log_finish) - np.array(model['process2'].log_start[:p2_finished_jobs])
process2_ct_mean = np.mean(process2_ct)
makespan = np.array(model['process2'].log_finish)- np.array(model['process1'].log_start[:p2_finished_jobs])
makespan = np.mean(makespan)
print('Average Service Time of Process1 : ',process1_ct_mean)
print('Average Service Time of Process2 : ',process2_ct_mean)
print('Average Makespan :',makespan)
"""

Result

process1 started processing part 1 at 0.00
process1 finished processing part 1 at 4.09
process2 started processing part 1 at 4.09
process1 started processing part 2 at 4.09
process2 finished processing part 1 at 4.76
process1 finished processing part 2 at 5.98
process2 started processing part 2 at 5.98
process1 started processing part 3 at 5.98
process2 finished processing part 2 at 7.44


.
.
.


process1 started processing part 30 at 94.53
process1 finished processing part 30 at 95.45
process1 started processing part 31 at 96.02
process2 finished processing part 29 at 97.77
process2 started processing part 30 at 97.77
process2 finished processing part 30 at 99.67
process1 finished processing part 31 at 99.95
process2 started processing part 31 at 99.95
process1 started processing part 32 at 99.95
Average Cycle Time of Process1 :  1.828995878846538
Average Cycle Time of Process2 :  1.1413979263623124
Average Makespan : 3.212144569240352


"""