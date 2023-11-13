import simpy
import pandas as pd
import random


class Part:
    def __init__(self, id):
        self.id = id
        self.step = 0
        self.process_list = ['process1', 'process2', 'sink']

class Source:
    def __init__(self, env, monitor, model, name, IAT):
        self.env = env
        self.monitor = monitor
        self.model = model
        self.name = name
        self.IAT = IAT
        self.part_id = 0
        self.env.process(self.processing())
        self.start_time = []

    def processing(self):
        while True:
            self.start_time.append(self.env.now)
            self.part_id += 1
            part = Part(self.part_id)
            self.monitor.record(time=self.env.now, part=part.id, process=self.name, event='part created')
            yield self.env.process(self.to_next_process(part))

            IAT = random.expovariate(1 / self.IAT)
            yield self.env.timeout(IAT)

    def to_next_process(self,part):
        yield self.model[part.process_list[part.step]].store.put(part)



class Process:
    def __init__(self, env, monitor, model, name, service_time, std_time, capacity):
        self.env = env
        self.monitor = monitor
        self.model = model
        self.name = name
        self.service_time = service_time
        self.std_time = std_time
        self.store = simpy.Store(env)
        self.machines = simpy.Store(env, capacity=capacity)
        for i in range(capacity):
            self.machines.put('resource'+str(i))
        self.env.process(self.processing())

    def processing(self):
        while True:
            machine = yield self.machines.get()
            part = yield self.store.get()
            self.env.process(self.servicing(part, machine))

    def servicing(self, part, machine):
        # for gamma distribution
        beta = self.std_time ** 2 / self.service_time
        alpha = self.service_time / beta
        service_time = random.gammavariate(alpha, beta)
        # if service_time < 0:
        #     print(service_time)

        self.monitor.record(time=self.env.now, part=part.id, process=self.name, event='service start', resource=machine)
        yield self.env.timeout(service_time)
        self.monitor.record(time=self.env.now, part=part.id, process=self.name, event='service finish', resource=machine)

        self.env.process(self.to_next_process(part, machine))

    def to_next_process(self, part, machine):
        part.step += 1
        yield self.model[part.process_list[part.step]].store.put(part)
        self.machines.put(machine)


class Sink:
    def __init__(self, env, monitor, model, name):
        self.env = env
        self.monitor = monitor
        self.model = model
        self.name = name
        self.store = simpy.Store(env)
        self.env.process(self.processing())

        self.end_time = []
        self.TH = 0

    def processing(self):
        while True:
            part = yield self.store.get()
            self.end_time.append(self.env.now)
            self.TH += 1
            self.monitor.record(time=self.env.now, part=part.id, process=self.name, event='part finish')


class Monitor:
    def __init__(self, filepath):
        self.filepath = filepath
        self.time = list()
        self.part = list()
        self.process = list()
        self.event = list()
        self.resource = list()

    def record(self, time, process=None, part=None, event=None, resource=None):
        self.time.append(time)
        self.part.append(part)
        self.process.append(process)
        self.event.append(event)
        self.resource.append(resource)

    def save_event_tracer(self):
        event_tracer = pd.DataFrame(columns=['Time', 'Part', 'Process', 'Event', 'Resource'])
        event_tracer['Time'] = self.time
        event_tracer['Part'] = self.part
        event_tracer['Process'] = self.process
        event_tracer['Event'] = self.event
        event_tracer['Resource'] = self.resource

        # event_tracer.to_csv(self.filepath)
        return event_tracer


if __name__ == '__main__':
    random.seed(42)

    IAT = 3

    service_time_1 = 2
    std_time_1 = 1
    service_time_2 = 1
    std_time_2 = 1.5

    capacity = 1
    simtime = 10000

    sum_total_CT = 0
    num_parts = 0

    env = simpy.Environment()
    monitor = Monitor('eventlog.csv')
    model = {}
    model['source'] = Source(env, monitor, model, 'source', IAT)
    model['process1'] = Process(env, monitor, model, 'process1', service_time_1, std_time_1, capacity)
    model['process2'] = Process(env, monitor, model, 'process2', service_time_2, std_time_2, capacity)
    model['sink'] = Sink(env, monitor, model, 'sink')

    env.run(until=simtime)

    print(monitor.save_event_tracer())

    for i in range(len(model['sink'].end_time)):
        sum_total_CT += model['sink'].end_time[i] - model['source'].start_time[i]
        num_parts += 1

    print('Average CT: ', sum_total_CT/num_parts)

"""
event log는 출력하는 방식을 사용하였으며, 최종 cycle time 계산 결과 6.25min이 나왔다.
Process 1과 Process 2의 분포는 감마분포를 사용하였으며,
분포 생성에는 평균 = alpha * beta, 분산 = alpha * beta^2임을 이용하여 alpha와 beta를 구하였다.
이 때 alpha와 beta는 각각 shape와 scale parameter이다.
"""