import simpy
# import numpy as np
import random
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

            IAT = random.expovariate(1 / self.IAT)
            yield self.env.timeout(IAT)

    def to_next_process(self,part):
        yield self.model[part.process_list[part.step]].store.put(part)


class Process:
    def __init__(self, env, model, name,service_time, capacity):
        self.env = env
        self.model = model
        self.name = name
        self.service_time = service_time
        self.store = simpy.Store(env)
        self.machines = simpy.Resource(env, capacity=capacity)
        self.env.process(self.processing())
        self.total_working_time = 0

    def processing(self):
        while True:
            req = self.machines.request()
            yield req
            part = yield self.store.get()
            self.env.process(self.servicing(part, req))

    def servicing(self, part, req):
        service_time = random.expovariate(1 / self.service_time)
        self.total_working_time += service_time
        # print(part.id, 'starts service for', self.name, 'at', self.env.now)
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
            self.part_count += 1


if __name__ == '__main__':
    IAT = 3
    service_time_1 = 30
    service_time_2 = 50
    service_time_3 = 40
    capacity = 1
    SIM_TIME = 1000

    best_utilization = 0

    for i in range(8, 15): # capacity of machine 1
        for j in range(8, 30): # capacity of machine 2
            for k in range(8, 30): # capacity of machine 3
                random.seed(42)
                env = simpy.Environment()
                model = {}
                model['source'] = Source(env, model, 'source', IAT)
                model['process1'] = Process(env, model, 'process1', service_time_1, capacity = (i + 1))
                model['process2'] = Process(env, model, 'process2', service_time_2, capacity = (j + 1))
                model['process3'] = Process(env, model, 'process3', service_time_3, capacity = (k + 1))
                model['sink'] = Sink(env, model, 'sink')

                env.run(until=SIM_TIME)

                if model['process1'].total_working_time / (i + 1) / SIM_TIME > 0.9 or model['process2'].total_working_time / (j + 1) / SIM_TIME > 0.9 or model['process3'].total_working_time / (k + 1) / SIM_TIME > 0.9:
                    continue
                else:
                    print("________________")
                    print("utilization: ", model['process1'].total_working_time / (i + 1) / SIM_TIME, model['process2'].total_working_time / (j + 1) / SIM_TIME, model['process3'].total_working_time / (k + 1) / SIM_TIME)
                    print("capacity: ", i + 1, j + 1, k + 1)

                total_utilization = model['process1'].total_working_time / (i + 1) / SIM_TIME + model['process2'].total_working_time / (j + 1) / SIM_TIME + model['process3'].total_working_time / (k + 1) / SIM_TIME

                if total_utilization > best_utilization:
                    best_utilization = total_utilization
                    best_capacity = [i + 1, j + 1, k + 1]
                    print("best utilization: ", best_utilization)
                    print("best capacity: ", best_capacity)

    SIM_TIME = 1000000

    random.seed(42)
    env = simpy.Environment()
    model = {}
    model['source'] = Source(env, model, 'source', IAT)
    model['process1'] = Process(env, model, 'process1', service_time_1, capacity=best_capacity[0])
    model['process2'] = Process(env, model, 'process2', service_time_2, capacity=best_capacity[1])
    model['process3'] = Process(env, model, 'process3', service_time_3, capacity=best_capacity[2])
    model['sink'] = Sink(env, model, 'sink')

    env.run(until=SIM_TIME)

"""
시뮬레이션 결과, machine 1의 capacity가 10, machine 2의 capacity가 17, machine 3의 capacity가 12일 때
각각의 utilization이 90%를 넘지 않으면서 가장 좋은 성능(0.86, 0.89, 0.86)을 보였다.
단, 이는 1000min의 시뮬레이션 결과이며, 1000000min의 시뮬레이션 결과는 조금 다를 수 있다.
다만, 시험 시간과 실행 시간의 한계로 위와 같이 코딩을 하였으며,
시간이 더 많이 주어진다면 실제로 1000000인 경우에 대해 최적의 값을 찾을 수 있을 것이라고 생각한다.

만약 위 두 결과의 최적 값이 다르다면 이는 확률적인 영향도 있을 것이고, 시뮬레이션 시간이 늘어남에 따라 초기 Process2, 3이 일을 하지 않는 시간의 비중이 줄어드는 영향도 있을 것이다.
따라서, 이를 고려한다면 실제 최적의 결과는 이보다 약간 더 작은 capacity에서 나올 가능성이 있다.
"""



