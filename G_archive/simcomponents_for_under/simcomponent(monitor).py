import simpy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


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

    def processing(self):
        while True:
            self.part_id += 1
            part = Part(self.part_id)
            self.monitor.record(time=self.env.now, part=part.id, process=self.name, event='part created')
            yield self.env.process(self.to_next_process(part))

            IAT = self.IAT
            yield self.env.timeout(IAT)

    def to_next_process(self,part):
        yield self.model[part.process_list[part.step]].store.put(part)



class Process:
    def __init__(self, env, monitor, model, name, setup_time, service_time, capacity):
        self.env = env
        self.monitor = monitor
        self.model = model
        self.name = name
        self.setup_time = setup_time
        self.service_time = service_time
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
        setup_time = self.setup_time

        self.monitor.record(time=self.env.now, part=part.id, process=self.name, event='setup start', resource=machine)
        yield self.env.timeout(setup_time)
        self.monitor.record(time=self.env.now, part=part.id, process=self.name, event='setup finish', resource=machine)

        service_time = self.service_time
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

    def processing(self):
        while True:
            part = yield self.store.get()
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

        event_tracer.to_csv(self.filepath)
        return event_tracer


if __name__ == '__main__':
    IAT = 4
    setup_time = 2
    service_time = 3
    capacity = 2

    env = simpy.Environment()
    monitor = Monitor('eventlog.csv')
    model = {}
    model['source'] = Source(env, monitor, model, 'source', IAT)
    model['process1'] = Process(env, monitor, model, 'process1', setup_time, service_time, capacity)
    model['process2'] = Process(env, monitor, model, 'process2', setup_time, service_time, capacity)
    model['sink'] = Sink(env, monitor, model, 'sink')

    env.run(until=100)

    monitor.save_event_tracer()