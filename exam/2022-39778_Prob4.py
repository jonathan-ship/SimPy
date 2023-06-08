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
        self.process_list = ['process1', 'process2', 'process3', 'sink']


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

            IAT = np.random.exponential(self.IAT) #IAT is exponential distribution
            yield self.env.timeout(IAT)

    def to_next_process(self,part):
        yield self.model[part.process_list[part.step]].store.put(part)


class Process:
    def __init__(self, env, model, name, service_time, capacity):
        self.env = env
        self.model = model
        self.name = name
        self.service_time = service_time
        self.capacity = capacity
        self.utilization = (self.service_time / IAT) * 100  # Calculate Utilization Rate (Arrival rate / Service rate = Service time / IAT)
        self.store = simpy.Store(env)
        self.machines = simpy.Resource(env, capacity=capacity)
        self.env.process(self.processing())

    def processing(self):
        while True:
            req = self.machines.request()
            yield req
            part = yield self.store.get()
            self.env.process(self.servicing(part, req))

        return utilization, capacity

    def servicing(self, part, req):
        service_time = np.random.exponential(self.service_time) #Service_time is exponential distribution
        if self.utilization > 90: #If Utilization exceed 90%
            self.capacity += 1 #Add machine number
            print(part.id, 'starts service for', self.name, 'at', self.env.now)
            yield self.env.timeout(service_time)
            print(part.id, 'finishes service for', self.name, 'at', self.env.now)

            self.env.process(self.to_next_process(part, req))

        else:
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
    IAT = 3
    service_time_1 = 30
    service_time_2 = 50
    service_time_3 = 40
    capacity_initial = 1

    env = simpy.Environment()
    model = {}
    model['source'] = Source(env, model, 'source', IAT)
    model['process1'] = Process(env, model, 'process1', service_time_1, capacity_initial)
    model['process2'] = Process(env, model, 'process2', service_time_2, capacity_initial)
    model['process3'] = Process(env, model, 'process3', service_time_3, capacity_initial)
    model['sink'] = Sink(env, model, 'sink')

    env.run(until=1000)

    print('Machine Number of Process 1 :', model['process1'].capacity)
    print('Utilization of Process 1 :', model['process1'].utilization)
    print('Machine Number of Process 2 :', model['process2'].capacity)
    print('Utilization of Process 2 :', model['process2'].utilization)
    print('Machine Number of Process 3 :', model['process3'].capacity)
    print('Utilization of Process 3 :', model['process3'].utilization)