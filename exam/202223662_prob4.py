import simpy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import random

Log = []

class Part:
    def __init__(self, id, enter_time):
        self.id = id
        self.enter_time = enter_time
        self.exit_time = None
        self.step = 0
        self.process_list = ['process1', 'process2', 'process3', 'sink']


class Source:
    def __init__(self, env, model, name, mean):
        self.env = env
        self.model = model
        self.name = name
        self.mean = mean
        self.part_id = 0
        self.env.process(self.processing())

    def processing(self):
        while True:
            self.part_id += 1
            part = Part(self.part_id, enter_time=self.env.now)
            # print(part.id, 'is created at', self.env.now)
            Log.append([])
            yield self.env.process(self.to_next_process(part))

            IAT = random.expovariate(1 / self.mean)
            yield self.env.timeout(IAT)

    def to_next_process(self,part):
        yield self.model[part.process_list[part.step]].store.put(part)


class Process:
    def __init__(self, env, model, name, mean, capacity=1):
        self.env = env
        self.model = model
        self.name = name
        self.mean_time = mean
        self.store = simpy.Store(env)
        self.machines = simpy.Resource(env, capacity=capacity)
        self.env.process(self.processing())

    def processing(self):
        while True:
            req = self.machines.request()
            yield req
            part = yield self.store.get()
            self.env.process(self.servicing(part, req))

    def servicing(self, part, req):
        service_time = random.expovariate(1 / self.mean_time)
        # print(part.id, 'starts service for', self.name, 'at', self.env.now)
        Log[part.id - 1].append(service_time)
        yield self.env.timeout(service_time)
        # print(part.id, 'finishes service for', self.name, 'at', self.env.now)

        self.env.process(self.to_next_process(part, req))

    def to_next_process(self, part, req):
        part.step += 1
        yield self.model[part.process_list[part.step]].store.put(part)
        self.machines.release(req)


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
            # print(part.id, 'finishes at', self.env.now)
            # Log[part.id - 1].append(self.env.now)
            self.part_count += 1
    
def find():
    SIM_TIME = 1000

    limit = 10

    rho_list2 = []
    for i in range(1, limit):
        t1 = []
        for j in range(1, limit):
            t2 = []
            for k in range(1, limit):
                env = simpy.Environment()
                random.seed(42)

                Log = []

                model = {}
                model['source'] = Source(env, model, 'source', 3)
                model['process1'] = Process(env, model, 'process1', 30, i)
                model['process2'] = Process(env, model, 'process2', 50, j)
                model['process3'] = Process(env, model, 'process3', 40, k)
                model['sink'] = Sink(env, model, 'sink')

                env.run(until=SIM_TIME)

                rho_list = np.zeros(3)

                for ii in Log:
                    for jj in range(len(ii)):
                        rho_list[jj] = rho_list[jj] + ii[jj]

                rho_list = rho_list / (SIM_TIME * np.array([i, j, k]))
                # print('-------------------------------------------------------------------')
                # print(num_machine)
                # print(rho_list)

                t2.append(rho_list)
            t1.append(t2)
        rho_list2.append(t1)

    rho_list2

if __name__ == '__main__':
    env = simpy.Environment()
    random.seed(42)

    SIM_TIME = 1000
    num_machine = np.array([13, 17, 12])

    model = {}
    model['source'] = Source(env, model, 'source', 3)
    model['process1'] = Process(env, model, 'process1', 30, num_machine[0])
    model['process2'] = Process(env, model, 'process2', 50, num_machine[1])
    model['process3'] = Process(env, model, 'process3', 40, num_machine[2])
    model['sink'] = Sink(env, model, 'sink')

    env.run(until=SIM_TIME)

    rho_list = np.zeros(3)

    for i in Log:
        for j in range(len(i)):
            rho_list[j] = rho_list[j] + i[j]

    rho_list = rho_list / (SIM_TIME * num_machine)
    print('-------------------------------------------------------------------')
    print(num_machine)
    print(rho_list)

    