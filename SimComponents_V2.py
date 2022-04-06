import simpy, os, random
import pandas as pd
import numpy as np
from collections import OrderedDict

save_path = '../result'
if not os.path.exists(save_path):
   os.makedirs(save_path)


#region Operation
class Operation(object):
    def __init__(self, name, time, proc_list):
        # 해당 operation의 이름
        self.id = name
        # 해당 operation의 시간
        self.time = time
        # 해당 operation이 가능한 process의 list
        self.proc_list = proc_list

    # Operation의 시간을 호출하기 위한 함수
    def get_time(self):
        if type(self.time) is str:
            return eval('np.random.'+self.time)
        else:
            return self.time
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
    def __init__(self, env, name, model, monitor, data=None, jobtype=None, IAT='expon(1)', num_parts=float('inf')):
        self.env = env
        self.name = name # 해당 Source의 이름
        self.model = model
        self.monitor = monitor
        self.data = data # Source가 생성하는 Part의 데이터(입력값 없을 시 jobtype을 통한 Part 생성)
        self.jobtype = jobtype # Source가 생산하는 Part의 jobtype(입력값 없을 시 data를 통한 Part 생성)
        self.IAT = IAT # Source가 생성하는 Part의 IAT(jobtype을 통한 Part 생성)
        self.num_parts = num_parts # Source가 생성하는 Part의 갯수(jobtype을 통한 Part 생성)

        self.rec = 0 # 생성된 Part의 갯수를 기록하는 변수
        self.action = env.process(self.run())

    def run(self):
        # data를 통한 Part 생성
        if self.data is not None:
            while True:
                part_data = self.data.pop(0)[0]  # Part 가져오기

                part = part_data[0]
                IAT = part_data[1] - self.env.now  # Part 시작시간에 맞춰 timeout
                if IAT > 0:
                    yield self.env.timeout(IAT)

                # record: part_created
                part.loc = self.name
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Part Created")

                # Routing Start
                self.model['Routing'].queue.put(part)  # Routing class로 put
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Routing Start")

                if len(self.data) == 0:  # 모든 블록의 일이 끝나면 Source에서의 활동 종료
                    print("all parts are sent at : ", self.env.now)
                    break
        # jobtype을 통한 Part 생성
        else:
            while self.rec < self.num_parts:
                part = Part(self.name+'_'+str(self.rec), self.jobtype)

                # record: part_created
                part.loc = self.name
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Part Created")

                # Routing start
                self.model['Routing'].queue.put(part) # Routing class로 put
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Routing Start")
                if type(self.IAT) is str:
                    IAT = eval('np.random.' + self.IAT)
                else:
                    IAT = self.IAT
                yield self.env.timeout(IAT)
                self.rec += 1
#endregion


#region Process
class Process(object):
    def __init__(self, env, name, model, monitor, capacity=float('inf'), priority=1, in_buffer=float('inf'),
                 out_buffer=float('inf')):
        # input data
        self.env = env
        self.name = name # 해당 프로세스의 이름
        self.model = model
        self.monitor = monitor
        self.capa = capacity # 해당 프로세스의 동시 작업 한도
        self.priority = priority # 해당 프로세스의 우선 순위

        # variable defined in class
        self.parts_sent = 0
        self.util_time = 0.0 # 프로세스의 가동 시간

        # buffer and machine
        self.in_part = simpy.FilterStore(env, capacity=in_buffer+capacity)

        if out_buffer == 0:
            self.out_part = None
        else:
            self.out_part = simpy.FilterStore(env, capacity=out_buffer)
        self.machines = simpy.Store(env, capacity=capacity)

        # Part가 Process로 들어오는 것을 감지하기 위한 Event
        self.run_event = simpy.Event(env)
        # get run functions in class
        env.process(self.run())

    # run function
    def run(self):
        # out_buffer가 없는 경우
        if self.out_part is None:
            while True:
                yield self.run_event
                self.env.process(self.work_without_outbuffer())
        # out_buffer가 있는 경우
        else:
            while True:
                yield self.run_event
                self.env.process(self.work_with_outbuffer())

    # without out_buffer
    def work_without_outbuffer(self):
        yield self.machines.put('using')
        put_None = self.in_part.put(None)
        if len(self.in_part.put_queue) != 0:
            self.in_part.put_queue.pop(-1)
            self.in_part.put_queue.insert(0, put_None)
        part = yield self.in_part.get(lambda x: x is not None)
        operation = part.requirements[part.step]
        proc_time = operation.get_time()

        # Process start and finish
        self.monitor.record(self.env.now, self.name, None, part_id=part.id, event=operation.id+" Start")
        yield self.env.timeout(proc_time)
        self.monitor.record(self.env.now, self.name, None, part_id=part.id, event=operation.id+" Finish")
        self.util_time += proc_time

        # Routing start
        self.model['Routing'].queue.put(part)
        self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Routing Start")

    # with out_buffer
    def work_with_outbuffer(self):
        yield self.machines.put('using')
        put_None = self.in_part.put(None)
        if len(self.in_part.put_queue) != 0:
            self.in_part.put_queue.pop(-1)
            self.in_part.put_queue.insert(0, put_None)
        part = yield self.in_part.get(lambda x: x is not None)
        operation = part.requirements[part.step]
        proc_time = operation.get_time()

        # Process start and finish
        self.monitor.record(self.env.now, self.name, None, part_id=part.id, event=operation.id+" Start")
        yield self.env.timeout(proc_time)
        self.monitor.record(self.env.now, self.name, None, part_id=part.id, event=operation.id+" Finish")
        self.util_time += proc_time

        # Routing start
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

    # run function
    def run(self):
        while True:
            part = yield self.queue.get()
            part.step += 1
            if part.step < len(part.requirements):
                # to routing function
                self.env.process(self.least_util(part))
            else:
                # to Sink
                self.env.process(self.put_sink(part))

    # Routing(least utilized)
    def least_util(self, part):
        # Select least utilized proc
        operation = part.requirements[part.step]
        proc_list = [self.model[proc] for proc in operation.proc_list]
        util_list = [proc.util_time / proc.capa for proc in proc_list]
        idx = util_list.index(min(util_list))
        next_proc = proc_list[idx]

        # To next process
        yield self.env.process(self.to_next_proc(part, next_proc))

    # to next proc function
    def to_next_proc(self, part, next_proc):
        # Part의 위치가 임의의 Process인 경우
        if part.loc in self.model.keys():
            pre_proc = self.model[part.loc]
            # Part의 현재 process가 without out_buffer인 경우
            if pre_proc.out_part is None:
                self.monitor.record(self.env.now, next_proc.name, None, part_id=part.id, event="Routing Finish")
                # to next process
                yield next_proc.in_part.put(part)
                next_proc.run_event.succeed()
                next_proc.run_event = simpy.Event(self.env)
                yield pre_proc.machines.get()
                yield pre_proc.in_part.get(lambda x: x is None)
                part.loc = next_proc.name
                self.monitor.record(self.env.now, next_proc.name, None, part_id=part.id, event="Part transferred")
            # Part의 현재 process가 with out_buffer인 경우
            else:
                self.monitor.record(self.env.now, next_proc.name, None, part_id=part.id, event="Routing Finish")
                # to next process
                yield next_proc.in_part.put(part)
                next_proc.run_event.succeed()
                next_proc.run_event = simpy.Event(self.env)
                yield pre_proc.out_part.get(lambda x: x.id == part.id)
                part.loc = next_proc.name
                self.monitor.record(self.env.now, next_proc.name, None, part_id=part.id, event="Part transferred")

        # Part의 위치가 임의의 Source인 경우
        else:
            self.monitor.record(self.env.now, next_proc.name, None, part_id=part.id, event="Routing Finish")
            yield next_proc.in_part.put(part)
            next_proc.run_event.succeed()
            next_proc.run_event = simpy.Event(self.env)
            part.loc = next_proc.name
            self.monitor.record(self.env.now, next_proc.name, None, part_id=part.id, event="Part transferred")

    def put_sink(self, part):
        if part.loc in self.model.keys():
            pre_proc = self.model[part.loc]
            # Part의 현재 process가 without out_buffer인 경우
            if pre_proc.out_part is None:
                self.model['Sink'].put(part)
                yield pre_proc.machines.get()
                yield pre_proc.in_part.get(lambda x: x is None)
            # Part의 현재 process가 with out_buffer인 경우
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

        # Sink를 통해 끝마친 Part의 갯수
        self.parts_rec = 0
        # 마지막 Part가 도착한 시간
        self.last_arrival = 0.0

    # put function
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
