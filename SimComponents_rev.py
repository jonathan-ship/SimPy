import simpy
import os
import random
import pandas as pd
import numpy as np
from collections import OrderedDict, namedtuple

save_path = '../result'
if not os.path.exists(save_path):
    os.makedirs(save_path)


class Resource(object):
    def __init__(self, env, tp_info, wf_info, model, monitor, delay_time):
        self.env = env
        self.model = model
        self.monitor = monitor
        self.delay_time = delay_time

        # resource 할당
        self.tp_store = simpy.FilterStore(env)
        self.wf_store = simpy.FilterStore(env)
        transporter = namedtuple("Transporter", "name, capa, v_loaded, v_unloaded")
        workforce = namedtuple("Workforce", "name, skill")
        for name in tp_info.keys():
            self.tp_store.put(transporter(name, tp_info[name]["capa"], tp_info[name]["v_loaded"], tp_info[name]["v_unloaded"]))
        for name in wf_info.keys():
            self.wf_store.put(workforce(name, wf_info[name]["skill"]))

        # resource 위치 파악
        self.tp_location = {}
        self.wf_location = {}
        for name in tp_info.keys():
            self.tp_location[name] = []
        for name in wf_info.keys():
            self.wf_location[name] = []

    def request_tp(self, process_requesting, next_process, distance_to_requesting, distance_to_destination, min_capa, part=None):
        self.monitor.record(self.env.now, process_requesting, None, part_id=part.id, event="tp_request")
        if len(self.tp_store.items) > 0:
            tp = yield self.tp_store.get(lambda item: item.capa == min_capa)
        else:
            tp_location_list = []
            for name in self.tp_location.keys():
                tp_location_list.append(self.tp_location[name][-1])
            location = random.choice(tp_location_list)
            tp = yield self.model[location].tp_store.get(lambda item: item.capa == min_capa)

        yield self.env.timeout(distance_to_requesting / tp.v_unloaded)
        self.monitor.record(self.env.now, process_requesting, None, part_id=part.id, event="tp_arriving")
        yield self.env.timeout(distance_to_destination / tp.v_loaded)
        self.monitor.record(self.env.now, process_requesting, None, part_id=part.id, event="tp_released")
        self.model[next_process].put(part)

        self.model[next_process].tp_store.put(tp)
        self.tp_location[tp.name].append(next_process)

    def request_wf(self, process_requesting):
        print(0)

    def delaying(self):
        yield self.env.timeout(self.delay_time)
        return


class Part(object):
    def __init__(self, name, data):
        # 해당 Part의 이름
        self.id = name
        # 작업 시간 정보
        self.data = data
        # 작업을 완료한 공정의 수
        self.step = 0


class Source(object):
    def __init__(self, env, parts, model, monitor):
        self.env = env
        self.name = 'Source'
        self.parts = parts  ## Part 클래스로 모델링 된 Part들이 list 형태로 저장
        self.model = model
        self.monitor = monitor

        self.action = env.process(self.run())

    def run(self):
        while True:
            part = self.parts.pop(0)

            IAT = part.data[(0, 'start_time')] - self.env.now
            if IAT > 0:
                yield self.env.timeout(part.data[(0, 'start_time')] - self.env.now)

            # record: part_created
            self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="part_created")
            # print(part.id, 'is created at ', self.env.now)
            # next process
            next_process = part.data[(part.step, 'process')]
            self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="part_transferred")
            self.model[next_process].buffer_to_machine.put(part)
            # print(part.id, 'is transferred to ', next_process, 'at ', self.env.now)

            if len(self.parts) == 0:
                print("all parts are sent at : ", self.env.now)

                break


class Process(object):
    def __init__(self, env, name, machine_num, model, monitor, resource=None, process_time=None, capacity=float('inf'),
                 routing_logic='cyclic', priority=None, capa_to_machine=float('inf'), capa_to_process=float('inf'),
                 MTTR=None, MTTF=None, delay_time=None):
        # input data
        self.env = env
        self.name = name
        self.model = model
        self.monitor = monitor
        self.resource = resource
        self.process_time = process_time[self.name] if process_time is not None else [None for _ in range(machine_num)]
        self.capa = capacity
        self.machine_num = machine_num
        self.routing_logic = routing_logic
        self.priority = priority[self.name] if priority is not None else [1 for _ in range(machine_num)]
        self.MTTR = MTTR[self.name] if MTTR is not None else [None for _ in range(machine_num)]
        self.MTTF = MTTF[self.name] if MTTF is not None else [None for _ in range(machine_num)]
        self.delay_time = delay_time[name] if delay_time is not None else None

        # variable defined in class
        self.parts_sent = 0
        self.machine_idx = 0
        self.len_of_server = []
        self.waiting_machine = OrderedDict()
        self.waiting_pre_process = OrderedDict()

        # buffer and machine
        self.buffer_to_machine = simpy.Store(env, capacity=capa_to_machine)
        self.buffer_to_process = simpy.Store(env, capacity=capa_to_process)
        self.machine = [Machine(env, '{0}_{1}'.format(self.name, i + 1), process_time=self.process_time[i],
                                priority=self.priority[i], out=self.buffer_to_process, waiting=self.waiting_machine,
                                monitor=monitor, MTTF=self.MTTF[i], MTTR=self.MTTR[i]) for i in range(self.machine_num)]

        # get run functions in class
        env.process(self.to_machine())
        env.process(self.to_process())

    def to_machine(self):
        routing = Routing(self.machine, priority=self.priority)
        while True:
            print('delaying start at', self.env.now, 'in ', self.name)
            if self.delay_time is not None:
                delaying_time = self.delay_time if type(self.delay_time) == float else self.delay_time()
                yield self.env.timeout(delaying_time)
            part = yield self.buffer_to_machine.get()
            print('{0} gets in in_buffer of {1} at {2}'.format(part.id, self.name, self.env.now))
            self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Process_entered")
            ## Rouring logic 추가 할 예정
            if self.routing_logic == 'priority':
                self.machine_idx = routing.priority()
            else:
                self.machine_idx = 0 if (self.parts_sent == 0) or (
                    self.machine_idx == self.machine_num - 1) else self.machine_idx + 1

            self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="routing_ended")
            self.machine[self.machine_idx].machine.put(part)
            print('{0} go to {1}_{2} at {3}'.format(part.id, self.name , self.machine_idx, self.env.now))

            # finish delaying of pre-process
            if (len(self.buffer_to_machine.items) < self.buffer_to_machine.capacity) and (len(self.waiting_pre_process) > 0):
                self.waiting_pre_process.popitem(last=False)[1].succeed()  # delay = (part_id, event)

    def to_process(self):
        while True:
            part = yield self.buffer_to_process.get()
            print('{0} gets in out_buffer of {1} at {2}'.format(part.id, self.name, self.env.now))
            # next process
            step = 1
            while not part.data[(part.step + step, 'process_time')]:
                if part.data[(part.step + step, 'process')] != 'Sink':
                    step += 1
                else:
                    break

            next_process_name = part.data[(part.step + step, 'process')]
            next_process = self.model[next_process_name]
            if next_process.__class__.__name__ == 'Process':
                # buffer's capacity of next process is full -> have to delay
                if len(next_process.buffer_to_machine.items) == next_process.buffer_to_machine.capacity:
                    next_process.waiting_preprocess[part.id] = self.env.event()
                    self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="delay_start_out_buffer")
                    yield next_process.waiting_preprocess[part.id]
                    self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="delay_finish_out_buffer")

                # part transfer
                next_process.buffer_to_machine.put(part)
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="part_transferred")
            else:
                next_process.put(part)
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="part_transferred")

            part.step += step
            print('{0} gets off to {1} at {2}'.format(part.id, next_process_name, self.env.now))

            if (len(self.buffer_to_process.items) < self.buffer_to_process.capacity) and (len(self.waiting_machine) > 0):
                self.waiting_machine.popitem(last=False)[1].succeed()  # delay = (part_id, event)


class Machine(object):
    def __init__(self, env, name, process_time, priority, out, waiting, monitor, MTTF, MTTR):
        # input data
        self.env = env
        self.name = name
        self.process_time = process_time
        self.priority = priority
        self.out = out
        self.waiting = waiting
        self.monitor = monitor
        self.MTTR = MTTR
        self.MTTF = MTTF

        # variable defined in class
        self.machine = simpy.Store(env, capacity=1)
        self.working_start = 0.0
        self.total_time = 0.0
        self.total_working_time = 0.0
        self.working = False  # whether machine's worked(True) or idled(False)
        self.broken = False  # whether machine is broken or not

        # get run functions in class
        self.action = env.process(self.work())
        if (self.MTTF is not None) and (self.MTTR is not None):
            env.process(self.break_machine(self.MTTF))

    def work(self):
        while True:
            self.broken = True
            part = yield self.machine.get()

            # if self.name[:-2] == 'LineHeating':
            #     print('{0} gets in {1} at {2}'.format(part.id, self.name, self.env.now))
            self.working = True
            process_name = self.name[:-2]

            # process_time
            if self.process_time is None:  # part에 process_time이 미리 주어지는 경우
                proc_time = part.data[(part.step, "process_time")]
            else:  # service time이 정해진 경우 --> 1) fixed time / 2) Stochastic-time
                proc_time = self.process_time if type(self.process_time) == float else self.process_time()

            while proc_time:
                try:
                    self.broken = False
                    ## working start
                    self.monitor.record(self.env.now, process_name, self.name, part_id=part.id, event="work_start")
                    self.working_start = self.env.now
                    yield self.env.timeout(proc_time)

                    ## working finish
                    self.monitor.record(self.env.now, process_name, self.name, part_id=part.id, event="work_finish")
                    self.total_working_time += self.env.now - self.working_start
                    self.broken = True
                    proc_time = 0.0

                except simpy.Interrupt:
                    self.broken = True
                    self.monitor.record(self.env.now, process_name, self.name, part_id=part.id,
                                        event="machine_broken")
                    print('{0} is broken at '.format(self.name), self.env.now)
                    proc_time -= self.env.now - self.working_start
                    if self.MTTR is not None:
                        repair_time = self.MTTR if type(self.MTTR) == float else self.MTTR()
                        yield self.env.timeout(repair_time)
                    self.monitor.record(self.env.now, process_name, self.name, part_id=part.id,
                                        event="machine_rerunning")
                    print(self.name, 'is solved at ', self.env.now)
                    self.broken = False

            self.working = False
            # start delaying at machine cause buffer_to_process is full
            if len(self.out.items) == self.out.capacity:
                self.waiting[part.id] = self.env.event()
                self.monitor.record(self.env.now, process_name, self.name, part_id=part.id,
                                    event="delay_start_machine")
                yield self.waiting[part.id]  # start delaying
                self.monitor.record(self.env.now, process_name, self.name, part_id=part.id,
                                    event="delay_finish_machine")

            # transfer to 'to_process' function
            self.out.put(part)
            self.monitor.record(self.env.now, process_name, self.name, part_id=part.id,
                                event="part_transferred")
            print('{0} gets off to {1} at {2}'.format(part.id, self.name, self.env.now))
            self.total_time += self.env.now - self.working_start

    def break_machine(self, mttf):
        while True:
            mttf_time = mttf if type(mttf) == float else mttf()
            yield self.env.timeout(mttf_time)
            if not self.broken:
                self.action.interrupt()
            if (self.monitor.event.count('completed') > 0) and (self.monitor.event.count('part_created') == self.monitor.event.count('completed')):
                break


class Sink(object):
    def __init__(self, env, monitor):
        self.env = env
        self.name = 'Sink'
        self.monitor = monitor

        # self.tp_store = simpy.FilterStore(env)  # transporter가 입고 - 출고 될 store
        self.parts_rec = 0
        self.last_arrival = 0.0

    def put(self, part):
        print('{0} gets in Sink at {1}'.format(part.id, self.env.now))
        self.parts_rec += 1
        self.last_arrival = self.env.now
        self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="completed")


class Monitor(object):
    def __init__(self, filepath):
        self.filepath = filepath  ## Event tracer 저장 경로

        self.time=[]
        self.event=[]
        self.part_id=[]
        self.process=[]
        self.subprocess=[]

    def record(self, time, process, subprocess, part_id=None, event=None):
        self.time.append(time)
        self.event.append(event)
        self.part_id.append(part_id)
        self.process.append(process)
        self.subprocess.append(subprocess)

    def save_event_tracer(self):
        event_tracer = pd.DataFrame(columns=['Time', 'Event', 'Part', 'Process', 'SubProcess'])
        event_tracer['Time'] = self.time
        event_tracer['Event'] = self.event
        event_tracer['Part'] = self.part_id
        event_tracer['Process'] = self.process
        event_tracer['SubProcess'] = self.subprocess
        event_tracer.to_csv(self.filepath)

        return event_tracer


class Routing(object):
    def __init__(self, server_list=None, priority=None):
        self.server_list = server_list
        self.idx_priority = np.array(priority)

    def priority(self):
        i = min(self.idx_priority)
        idx = 0
        while i <= max(self.idx_priority):
            min_idx = np.argwhere(self.idx_priority == i)  # priority가 작은 숫자의 index부터 추출
            idx_min_list = min_idx.flatten().tolist()
            # 해당 index list에서 machine이 idling인 index만 추출
            idx_list = list(filter(lambda i: (self.server_list[i].working == False), idx_min_list))
            if len(idx_list) > 0:  # 만약 priority가 높은 machine 중 idle 상태에 있는 machine이 존재한다면
                idx = random.choice(idx_list)
                break
            else:  # 만약 idle 상태에 있는 machine이 존재하지 않는다면
                if i == max(self.idx_priority):  # 그 중 모든 priority에 대해 machine이 가동중이라면
                    idx = random.choice([j for j in range(len(self.idx_priority))])  # 그냥 무작위 배정
                else:
                    i += 1  # 다음 priority에 대하여 따져봄
        return idx
