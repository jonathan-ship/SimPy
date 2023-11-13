"""
Jiwon Baek
Topics in Ship Production Engineering Final Exam
Problem 4
"""


import simpy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


class Part:
    def __init__(self, id, enter_time):
        self.id = id
        self.enter_time = enter_time


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
        yield self.env.timeout(servicetime)
        self.log_finish.append(self.env.now)
        self.env.process(self.to_next_process(part, req, self.next_process_name))

    def to_next_process(self, part, req, next_process_name):
        yield self.model[next_process_name].store.put(part)
        self.machines.release(req)


np.random.seed(5)

mean_IAT = 3
NUM_M1 = []
NUM_M2 = []
NUM_M3 = []
U1_list = []
U2_list = []
U3_list = []
finished_list = []
MEAN_P1 = 30
MEAN_P2 = 50
MEAN_P3 = 40
SIMTIME = 1000


for m1 in range(10, 21):
    for m2 in range(17, 21):
        for m3 in range(14, 21):
            env = simpy.Environment()
            model = {}
            model['source'] = Source(env, model, 'source', mean_IAT)
            model['process1'] = Process(env, model, 'process1', MEAN_P1, m1,'process2')
            model['process2'] = Process(env, model, 'process2', MEAN_P2, m2,'process3')
            model['process3'] = Process(env, model, 'process3', MEAN_P3, m3,'sink')
            model['sink'] = Sink(env, model, 'sink')
            env.run(until=SIMTIME)

            finished = model['sink'].part_count
            U1 = model['process1'].total_working_time / (SIMTIME * m1)
            U2 = model['process2'].total_working_time / (SIMTIME * m2)
            U3 = model['process3'].total_working_time / (SIMTIME * m3)
            finished_list.append(finished)
            
            NUM_M1.append(m1)
            NUM_M2.append(m2)
            NUM_M3.append(m3)
            U1_list.append(U1)
            U2_list.append(U2)
            U3_list.append(U3)

            # Utilization
            print('-' * 45)
            print('M1 : %d, M2 : %d, M3 = %d' % (m1, m2, m3))
            print('Total FInished Jobs :', finished)
            print('Utilization of Process 1 :', np.round(U1, 3))
            print('Utilization of Process 2 :', np.round(U2, 3))
            print('Utilization of Process 3 :', np.round(U3, 3))

"""
Recording Results
"""
print('Recording Simulation Results...')
result = np.array([NUM_M1, U1_list, NUM_M2, U2_list, NUM_M3, U3_list, finished_list]).T
result = pd.DataFrame(result, columns=['NUM_M1', 'U1', 'NUM_M2', 'U2', 'NUM_M3', 'U3', 'TH'])

"""
Find Combination that maximizes utilization without exceeding 90%
"""
print('<Best Result>')
best_result = result[(result['U1'] < 0.9) & (result['U2'] < 0.9) & (result['U3'] < 0.9)]
best_result = best_result[(best_result['U1'] > 0.75) & (best_result['U2'] > 0.75) & (best_result['U3'] > 0.75)]
print(best_result)


"""

(Result when simulation time = 1000)


     NUM_M1        U1  NUM_M2        U2  NUM_M3        U3     TH
28     11.0  0.853167    17.0  0.855193    14.0  0.842288  284.0
36     11.0  0.875574    18.0  0.822716    15.0  0.773082  277.0
43     11.0  0.840645    19.0  0.888884    15.0  0.855900  298.0
49     11.0  0.872594    20.0  0.765647    14.0  0.863331  273.0
63     12.0  0.850591    18.0  0.787826    14.0  0.893664  268.0
91     13.0  0.770854    18.0  0.809963    14.0  0.858428  262.0
98     13.0  0.754675    19.0  0.873413    14.0  0.823849  272.0
99     13.0  0.815887    19.0  0.794048    15.0  0.804136  296.0
109    13.0  0.790181    20.0  0.793409    18.0  0.761012  307.0
120    14.0  0.769283    18.0  0.885036    15.0  0.824847  275.0
163    15.0  0.755946    20.0  0.879687    16.0  0.861041  316.0




"""