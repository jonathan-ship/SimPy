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
        self.process_list = ['process1', 'process2', 'sink']


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
            print(part.id, 'is created at', self.env.now)
            Log.append([self.env.now])
            yield self.env.process(self.to_next_process(part))

            IAT = random.expovariate(1/self.mean)
            yield self.env.timeout(IAT)

    def to_next_process(self,part):
        yield self.model[part.process_list[part.step]].store.put(part)


class Process:
    def __init__(self, env, model, name, mean, std, capacity=1):
        self.env = env
        self.model = model
        self.name = name
        self.mean_time = mean
        self.std_time = std
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
        service_time = random.gammavariate(self.mean_time, self.std_time)
        print(part.id, 'starts service for', self.name, 'at', self.env.now)
        yield self.env.timeout(service_time)
        print(part.id, 'finishes service for', self.name, 'at', self.env.now)

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
            print(part.id, 'finishes at', self.env.now)
            Log[part.id - 1].append(self.env.now)
            self.part_count += 1
    

if __name__ == '__main__':
    env = simpy.Environment()
    random.seed(42)

    SIM_TIME = 1000

    model = {}
    model['source'] = Source(env, model, 'source', 3)
    model['process1'] = Process(env, model, 'process1', 2, 1)
    model['process2'] = Process(env, model, 'process2', 1, 1.5)
    model['sink'] = Sink(env, model, 'sink')

    env.run(until=SIM_TIME)

    CT_list = []
    for i in Log:
        if len(i) == 2:
            CT = i[1] - i[0]
        else:
            CT = SIM_TIME - i[0]

        CT_list.append(CT)

    print('-------------------------------------------------------------------')
    print('CT:', np.mean(CT_list))