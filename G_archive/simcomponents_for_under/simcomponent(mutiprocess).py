import simpy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


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
            print(part.id, 'is created at', self.env.now)
            yield self.env.process(self.to_next_process(part))

            IAT = self.IAT
            yield self.env.timeout(IAT)

    def to_next_process(self,part):
        yield self.model[part.process_list[part.step]].store.put(part)


class Process:
    def __init__(self, env, model, name, setup_time, service_time, capacity):
        self.env = env
        self.model = model
        self.name = name
        self.setup_time = setup_time
        self.service_time = service_time
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

        service_time = self.service_time
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
            self.part_count += 1


if __name__ == '__main__':
    IAT = 4
    setup_time = 2
    service_time = 3
    capacity = 1

    env = simpy.Environment()
    model = {}
    model['source'] = Source(env, model, 'source', IAT)
    model['process1'] = Process(env, model, 'process1', setup_time, service_time, capacity)
    model['process2'] = Process(env, model, 'process2', setup_time, service_time, capacity)
    model['sink'] = Sink(env, model, 'sink')

    env.run(until=100)

    print('TH:', model['sink'].part_count)