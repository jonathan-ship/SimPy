import simpy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

part_list = []

class Part:
    def __init__(self, id, enter_time):
        self.id = id
        self.enter_time = enter_time
        self.exit_time = None
        self.step = 0
        self.process_list = ['process1', 'process2', 'sink']


class Source:
    def __init__(self, env, model, name, IAT):
        self.env = env
        self.model = model
        self.name = name
        self.IAT = IAT
        self.part_id = 0
        self.env.process(self.processing())

    def processing(self):
        while True:
            self.part_id += 1
            part = Part(self.part_id, enter_time=self.env.now)
            part_list.append(part)
            print(part.id, 'is created at', self.env.now)
            yield self.env.process(self.to_next_process(part))

            arrival_time = np.random.exponential(self.IAT)
            yield self.env.timeout(arrival_time)

    def to_next_process(self,part):
        yield self.model[part.process_list[part.step]].store.put(part)


class Process:
    def __init__(self, env, model, name, setup_time, service_time_mean, service_time_std, capacity):
        self.env = env
        self.model = model
        self.name = name
        self.setup_time = setup_time
        self.service_time_mean = service_time_mean
        self.service_time_std = service_time_std
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
        setup_time = self.setup_time
        print(part.id, 'starts setup for', self.name, 'at', self.env.now)
        yield self.env.timeout(setup_time)
        print(part.id, 'finishes setup for', self.name, 'at', self.env.now)

        service_time = np.random.normal(self.service_time_mean, self.service_time_std)
        if service_time < 0:
            service_time = 0.01
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
            part.exit_time = self.env.now
            print(part.id, 'finishes at', self.env.now)
            self.part_count += 1


if __name__ == '__main__':
    IAT = 3
    setup_time = 0
    service_time = 3
    capacity = 1

    service_time_mean1 = 2
    service_time_std1 = 1.0

    service_time_mean2 = 1
    service_time_std2 = 1.5

    env = simpy.Environment()
    model = {}
    model['source'] = Source(env, model, 'source', IAT)
    model['process1'] = Process(env, model, 'process1', setup_time, service_time_mean1, service_time_std1, capacity)
    model['process2'] = Process(env, model, 'process2', setup_time, service_time_mean2, service_time_std2, capacity)
    model['sink'] = Sink(env, model, 'sink')

    env.run(until=100)

    print('TH:', model['sink'].part_count)

    CT_list = []

    for part in part_list:
        if part.exit_time is None:
            continue
        CT = part.exit_time - part.enter_time
        print(part.id, 'CT:', CT)
        CT_list.append(CT)

    print('CT mean:', np.mean(CT_list))
