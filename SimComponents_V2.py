import simpy, os, random
import pandas as pd
import numpy as np
from collections import OrderedDict

save_path = '../result'
if not os.path.exists(save_path):
   os.makedirs(save_path)


#region Work
class Operation(object):
    def __init__(self, name, time, proc_list):
        # 해당 operation의 이름
        self.id = name
        # 해당 operation의 시간
        self.time = time
        # 해당 operation이 가능한 process의 list
        self.proc_list = proc_list
#endregion


#region Part
class Part(object):
    def __init__(self, name, requirements):
        # 해당 Part의 이름
        self.id = name
        # 작업 정보, production requirements
        self.requirements = requirements
        # 작업을 완료한 공정의 수
        self.step = -1
        # Part의 현재 위치
        self.loc = None
#endregion


#region Source
class Source(object):
    def __init__(self, env, name, model, monitor, data=None, jobtype=None, IAT=0):
        self.env = env
        self.name = name
        self.model = model
        self.monitor = monitor
        self.data = data
        self.jobtype = jobtype
        self.IAT = IAT

        self.action = env.process(self.run())

    def run(self):
        if self.data is not None:
            while True:
                part_data = self.data.pop(0)[0]  # Part 가져오기

                part = part_data[0]
                IAT = part_data[1] - self.env.now  # 블록 시작시간에 맞춰 timeout
                if IAT > 0:
                    yield self.env.timeout(IAT)

                # record: part_created
                part.loc = self.name
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Part Created")

                # next process
                self.model['Routing'].queue.put(part)  # 첫 번째 Process
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Routing Start")

                if len(self.data) == 0:  # 모든 블록의 일이 끝나면 Source에서의 활동 종료
                    print("all parts are sent at : ", self.env.now)
                    break

        else:
            i = 0
            while True:
                part = Part(self.name+'_'+str(i), self.jobtype)

                # record: part_created
                part.loc = self.name
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Part Created")

                # next process
                self.model['Routing'].queue.put(part)  # 첫 번째 Process
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Routing Start")
                yield self.env.timeout(self.IAT)
                i += 1
#endregion


#region Process
class Process(object):
    def __init__(self, env, name, model, monitor, capacity=float('inf'), priority=1, in_buffer=float('inf'),
                 out_buffer=float('inf')):
        # input data
        self.env = env
        self.name = name
        self.model = model
        self.monitor = monitor
        self.capa = capacity
        self.priority = priority

        # variable defined in class
        self.parts_sent = 0
        self.util_time = 0.0

        # buffer and machine
        self.in_part = simpy.FilterStore(env, capacity=in_buffer+capacity)

        if out_buffer == 0:
            self.out_part = None
        else:
            self.out_part = simpy.FilterStore(env, capacity=out_buffer)
        self.machines = simpy.Store(env, capacity=capacity)

        # get run functions in class
        env.process(self.run())

    # run function
    def run(self):
        if self.out_part is None:
            # out-buffer의 capacity가 0일 때
            while True:
                yield self.machines.put('using')
                put_None = self.in_part.put(None)
                if len(self.in_part.put_queue) != 0:
                    self.in_part.put_queue.pop(-1)
                    self.in_part.put_queue.insert(0, put_None)
                part = yield self.in_part.get(lambda x: x is not None)
                proc_time = part.requirements[part.step].time
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Process Start")
                yield self.env.timeout(proc_time)
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Process Finish")
                self.util_time += proc_time

                self.model['Routing'].queue.put(part)
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Routing Start")
        else:
            # out-buffer의 capacity가 0이 아닐 때
            while True:
                yield self.machines.put('using')
                put_None = self.in_part.put(None)
                if len(self.in_part.put_queue) != 0:
                    self.in_part.put_queue.pop(-1)
                    self.in_part.put_queue.insert(0, put_None)
                part = yield self.in_part.get(lambda x: x is not None)
                proc_time = part.requirements[part.step].time

                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Process Start")
                yield self.env.timeout(proc_time)
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Process Finish")
                self.util_time += proc_time

                yield self.out_part.put(part)
                yield self.model['Routing'].queue.put(part)
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Routing Start")
                yield self.in_part.get(lambda x: x is None)
                yield self.machines.get()
#endregion


#region Routing
class Routing(object):
    def __init__(self, env, model, monitor):
        self.env = env
        self.name = 'Routing'
        self.model = model
        self.monitor = monitor

        self.queue = simpy.Store(env)

        env.process(self.run())

    def run(self):
        while True:
            part = yield self.queue.get()
            part.step += 1
            if part.step < len(part.requirements):
                self.env.process(self.least_util(part))
            else:
                self.env.process(self.put_sink(part))

    def least_util(self, part):
        operation = part.requirements[part.step]
        proc_list = [self.model[proc] for proc in operation.proc_list]
        util_list = [proc.util_time / proc.capa for proc in proc_list]
        idx = util_list.index(min(util_list))
        next_proc = proc_list[idx]
        yield self.env.process(self.to_next_proc(part, next_proc))

    def to_next_proc(self, part, next_proc):
        if part.loc in self.model.keys():
            pre_proc = self.model[part.loc]
            if pre_proc.out_part is None:
                self.monitor.record(self.env.now, next_proc.name, None, part_id=part.id, event="Routing Finish")
                yield next_proc.in_part.put(part)
                yield pre_proc.machines.get()
                yield pre_proc.in_part.get(lambda x: x is None)
                part.loc = next_proc.name
                self.monitor.record(self.env.now, next_proc.name, None, part_id=part.id, event="Part transferred")
            else:
                self.monitor.record(self.env.now, next_proc.name, None, part_id=part.id, event="Routing Finish")
                yield next_proc.in_part.put(part)
                yield pre_proc.out_part.get(lambda x: x.id == part.id)
                part.loc = next_proc.name
                self.monitor.record(self.env.now, next_proc.name, None, part_id=part.id, event="Part transferred")
        else:
            self.monitor.record(self.env.now, next_proc.name, None, part_id=part.id, event="Routing Finish")
            yield next_proc.in_part.put(part)
            part.loc = next_proc.name
            self.monitor.record(self.env.now, next_proc.name, None, part_id=part.id, event="Part transferred")

    def put_sink(self, part):
        if part.loc in self.model.keys():
            pre_proc = self.model[part.loc]
            if pre_proc.out_part is None:
                self.model['Sink'].put(part)
                yield pre_proc.machines.get()
                yield pre_proc.in_part.get(lambda x: x is None)
            else:
                self.model['Sink'].put(part)
                yield pre_proc.out_part.get(lambda x: x.id == part.id)
#endregion


#region Sink
class Sink(object):
    def __init__(self, env, monitor):
        self.env = env
        self.name = 'Sink'
        self.monitor = monitor

        self.parts_rec = 0
        self.last_arrival = 0.0

    def put(self, part):
        self.parts_rec += 1
        self.last_arrival = self.env.now
        self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Part Completed")
#endregion


#region Monitor
class Monitor(object):
    def __init__(self, filepath):
        self.filepath = filepath  ## Event tracer 저장 경로

        self.time = list()
        self.event = list()
        self.part = list()
        self.process_name = list()
        self.machine_name = list()

    def record(self, time, process, machine, part_id=None, event=None):
        self.time.append(time)
        self.event.append(event)
        self.part.append(part_id)
        self.process_name.append(process)
        self.machine_name.append(machine)

    def save_event_tracer(self):
        event_tracer = pd.DataFrame(columns=['Time', 'Event', 'Part', 'Process', 'Machine'])
        event_tracer['Time'] = self.time
        event_tracer['Event'] = self.event
        event_tracer['Part'] = self.part
        event_tracer['Process'] = self.process_name
        event_tracer['Machine'] = self.machine_name

        event_tracer.to_csv(self.filepath)

        return event_tracer

#endregion
