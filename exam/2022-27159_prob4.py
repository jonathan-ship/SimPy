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
            # print(part.id, 'is created at', self.env.now)
            yield self.env.process(self.to_next_process(part))

            arrival_time = np.random.exponential(self.IAT)
            yield self.env.timeout(arrival_time)

    def to_next_process(self, part):
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

        self.processing_time = 0

    def processing(self):
        while True:
            req = self.machines.request()
            yield req
            part = yield self.store.get()
            self.env.process(self.servicing(part, req))

    def servicing(self, part, req):
        setup_time = self.setup_time
        # print(part.id, 'starts setup for', self.name, 'at', self.env.now)
        yield self.env.timeout(setup_time)
        # print(part.id, 'finishes setup for', self.name, 'at', self.env.now)

        service_time = np.random.exponential(self.service_time)
        # print(part.id, 'starts service for', self.name, 'at', self.env.now)
        yield self.env.timeout(service_time)
        # print(part.id, 'finishes service for', self.name, 'at', self.env.now)

        self.processing_time += setup_time + service_time

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
            self.part_count += 1


def calc_utilization_rate(processing_time, sim_time):
    return processing_time / sim_time


if __name__ == '__main__':
    IAT = 3
    setup_time = 0
    sim_time = 1000000

    # maximize the sum of utilization rate of machine 1, 2, 3
    # but don't exceed 0.9 each

    best_sum = 0

    best_u_rate = [0, 0, 0]

    best_ijk = [0, 0, 0]

    test_num = 10

    for i in range(test_num, 1, -1):
        for j in range(test_num, 0, -1):
            for k in range(test_num, 0, -1):

                env = simpy.Environment()
                model = {}
                model['source'] = Source(env, model, 'source', IAT)
                model['process1'] = Process(env, model, 'process1', setup_time, 30, i)
                model['process2'] = Process(env, model, 'process2', setup_time, 50, j)
                model['process3'] = Process(env, model, 'process2', setup_time, 40, k)
                model['sink'] = Sink(env, model, 'sink')

                env.run(until=sim_time)

                u_i = calc_utilization_rate(model['process1'].processing_time, sim_time)
                u_j = calc_utilization_rate(model['process2'].processing_time, sim_time)
                u_k = calc_utilization_rate(model['process3'].processing_time, sim_time)

                if u_i > 0.9 or u_j > 0.9 or u_k > 0.9:
                    continue

                sum = u_i + u_j + u_k
                if sum > best_sum:
                    best_sum = sum
                    best_u_rate = [u_i, u_j, u_k]
                    best_ijk = [i, j, k]

    # print('TH:', model['sink'].part_count)


    print('best u_rate:', best_u_rate)
    print('best configuration:', best_ijk)