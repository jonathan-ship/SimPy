import simpy
import random
import numpy as np

class Part:
    def __init__(self, id, enter_time):
        self.id = id
        self.enter_time = enter_time
        self.exit_time = None
        self.step = 0
        self.process_list = ['process1', 'process2', 'sink']

class Source:
    def __init__(self, env, model, IAT):
        self.env=env
        self.model=model
        self.IAT=IAT
        self.part_id=0
        self.process=env.process(self.processing())

    def processing(self):
        while True:
            self.part_id += 1
            part = Part(self.part_id, self.env.now)
            print(part.id, 'is created at', self.env.now)
            yield self.env.process(self.to_next_process(part))

            IAT = self.IAT
            yield self.env.timeout(IAT)

    def to_next_process(self, part):
        yield self.model[part.process_list[part.step]].store.put(part)

class Process:
    def __init__(self,env,model,name,service_time,repair_time,time_to_failure,capacity):
        self.env=env
        self.model=model
        self.name=name
        self.service_time=service_time
        self.store=simpy.Store(env)
        self.repair_time=repair_time
        self.time_to_failure=time_to_failure
        self.machines=simpy.Resource(env,capacity=capacity)
        self.env.process(self.processing())
        self.broken=False

    def processing(self):
        while True:
            try:
                req=self.machines.request()
                yield req
                part = yield self.store.get()
                print(part.id, 'is assigned to', self.name, 'at', self.env.now)
                yield self.env.process(self.to_next_process(part))
            except simpy.Interrupt:
                self.broken=True
                self.env.timeout(self.repair_time)
                self.broken=False


    def servicing(self,part,req):

        service_time = self.service_time
        print(part.id, 'starts processing for', self.name, 'at', self.env.now)
        yield self.env.timeout(service_time)
        print(part.id, 'finishes processing for', self.name, 'at', self.env.now)

        self.env.process(self.to_next_process(part, req))

    def break_machine(self,part,req):
        while True:
            yield self.env.timeout(random.expovariate(self.time_to_failure))
            if not self.broken:
                self.process.interrupt()

    def to_next_process(self,part,req):
        part.step+=1
        yield self.model[part.process_list[part.step]].store.put(part)
        self.machines.release(req)

class Sink:
    def __init__(self,env,model,name):
        self.env=env
        self.model=model
        self.name=name
        self.store=simpy.Store(env)
        self.env.process(self.processing())

        self.part_count = 0

    def processing(self):
        while True:
            part = yield self.store.get()
            print(part.id, 'is finished at', self.env.now)
            self.part_count += 1

#input
c_a1=1

#process1
service_time_1=19/60
c_01=0.25
std_service_time_1=service_time_1*c_01
MTBF1=48
Break_mean_1=1/MTBF1
MTTR1=8 #expovariate

#process2
service_time_2=22/60
c_02=1.0
std_service_time_2=service_time_2*c_02
MTBF2=3.3
Break_mean_2=1/MTBF2
MTTR2=10/60 #expovariate

Throughput=2.4
arrival_rate=Throughput

env=simpy.Environment()
model={}
model['source']=Source(env,model,1/arrival_rate)
model['process1']=Process(env,model,'process1',t_01,c_01,c_a1)