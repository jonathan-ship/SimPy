import simpy
import random
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

            IAT = random.expovariate(1 / self.IAT)

            yield self.env.timeout(IAT)

    def to_next_process(self,part):
        yield self.model[part.process_list[part.step]].store.put(part)


class Process:
    def __init__(self, env, model, name, service_time, variance_factor, MTTR, MTBF, capacity):
        self.env = env
        self.model = model
        self.name = name
        self.service_time = service_time
        self.variance_factor = variance_factor
        self.MTTR = MTTR
        self.MTBF = MTBF
        self.store = simpy.Store(env)
        self.machines = simpy.Resource(env, capacity=capacity)
        self.env.process(self.processing())
        self.broken = False

    def processing(self):
        while True:
            req = self.machines.request()
            yield req
            part = yield self.store.get()
            self.env.process(self.servicing(part, req))
            self.env.process(self.break_machine())

    def servicing(self, part, req):
        service_time = random.normalvariate(self.service_time, self.variance_factor ** 0.5 * self.service_time)
        if service_time < 0:
            service_time = 0
        while service_time:
            try:
                start = self.env.now
                yield self.env.timeout(service_time)
                service_time = 0  # Set to 0 to exit while loop.

            except simpy.Interrupt:
                self.broken = True
                service_time -= self.env.now - start  # How much time left?

                # Request a repairman. This will preempt its "other_job".
                with simpy.PreemptiveResource(env, capaity = 1).request(priority=1) as req:
                    yield req
                    yield self.env.timeout(random.expovariate(1 / self.MTTR))

                self.broken = False

        self.env.process(self.to_next_process(part, req))

    def to_next_process(self, part, req):
        part.step += 1
        yield self.model[part.process_list[part.step]].store.put(part)
        self.machines.release(req)

    def break_machine(self):
        while True:
            yield self.env.timeout(random.expovariate(1 / self.MTBF))
            if not self.broken:
                # Only break the machine if it is currently working.
                self.env.process.interrupt(self.servicing())

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
    random.seed(42)

    IAT = 1 / (2.4 / 60) # min / EA
    service_time_1 = 19 # min
    service_time_2 = 22 # min
    variance_1 = 0.25
    variance_2 = 1.0
    MTBF_1 = 48 * 60 # min
    MTTR_1 = 8 * 60 # min
    MTBF_2 = 3.3 * 60 # min
    MTTR_2 = 10 # min
    capacity = 1

    env = simpy.Environment()
    model = {}
    model['source'] = Source(env, model, 'source', IAT)
    model['process1'] = Process(env, model, 'process1', service_time_1, variance_1, MTTR_1, MTBF_1, capacity)
    model['process2'] = Process(env, model, 'process2', service_time_2, variance_2, MTTR_2, MTBF_2, capacity)
    model['sink'] = Sink(env, model, 'sink')

    env.run(until=10000)


"""
theoretical하게 구하는 것은 M/G/1 model의 공식을 사용하여 구하면 되고,
위와 같은 방법으로 Simpy를 이용한 simulation을 구현하여 통계치들을 구한 후 두 값을 비교하려 하였습니다.

다만, 문법적 오류를 잡지 못해 끝까지 문제를 해결하지 못하였습니다.
"""
