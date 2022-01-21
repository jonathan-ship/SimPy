import simpy
import os
import random
import time
import pandas as pd
import numpy as np
from collections import OrderedDict, namedtuple

save_path = '../result'
if not os.path.exists(save_path):
   os.makedirs(save_path)


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
            part = self.parts.pop(0)  # Part 가져오기

            IAT = part.data[(0, 'start_time')] - self.env.now  # 블록 시작시간에 맞춰 timeout
            if IAT > 0:
                yield self.env.timeout(part.data[(0, 'start_time')] - self.env.now)

            # record: part_created
            self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Part Created")

            # next process
            next_process = part.data[(part.step, 'process')]  # 첫 번째 Process
            self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Source to Process")
            self.model[next_process].buffer_to_machine.put(part)

            if len(self.parts) == 0:  # 모든 블록의 일이 끝나면 Source에서의 활동 종료
                print("all parts are sent at : ", self.env.now)
                break


class Process(object):
    def __init__(self, env, name, machine_num, model, monitor, process_time=None, capacity=float('inf'),
                 routing_logic='cyclic', priority=None, capa_to_machine=float('inf'), capa_to_process=float('inf'),
                 MTTR=None, MTTF=None, initial_broken_delay=None, delay_time=None):
        # input data
        self.env = env
        self.name = name
        self.model = model
        self.monitor = monitor
        self.capa = capacity
        self.machine_num = machine_num
        self.routing_logic = routing_logic
        self.process_time = process_time[self.name] if process_time is not None else [None for _ in range(machine_num)]
        self.priority = priority[self.name] if priority is not None else [1 for _ in range(machine_num)]
        self.MTTR = MTTR[self.name] if MTTR is not None else [None for _ in range(machine_num)]
        self.MTTF = MTTF[self.name] if MTTF is not None else [None for _ in range(machine_num)]
        self.initial_broken_delay = initial_broken_delay[self.name] if initial_broken_delay is not None else [None for _ in range(machine_num)]
        self.delay_time = delay_time[name] if delay_time is not None else None

        # variable defined in class
        self.parts_sent = 0
        self.parts_sent_to_machine = 0
        self.machine_idx = 0
        self.len_of_server = []
        self.waiting_machine = OrderedDict()
        self.waiting_pre_process = OrderedDict()

        # buffer and machine
        self.buffer_to_machine = simpy.Store(env, capacity=capa_to_machine)
        self.buffer_to_process = simpy.Store(env, capacity=capa_to_process)
        self.machine = [Machine(env, '{0}_{1}'.format(self.name, i), self.name, process_time=self.process_time[i],
                                priority=self.priority[i], out=self.buffer_to_process,
                                waiting=self.waiting_machine, monitor=monitor, MTTF=self.MTTF[i], MTTR=self.MTTR[i],
                                initial_broken_delay=self.initial_broken_delay[i]) for i in range(machine_num)]


        # get run functions in class
        env.process(self.to_machine())
        env.process(self.to_process())

    # In-Buffer / Put Part into its Machine
    def to_machine(self):
        while True:
            routing = Routing(priority=self.priority)
            if self.delay_time is not None:
                delaying_time = self.delay_time if type(self.delay_time) == float else self.delay_time()
                yield self.env.timeout(delaying_time)
            part = yield self.buffer_to_machine.get()
            self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Process In")

            # Rouring logic에 맞추어 다음 machine index 선택
            if self.routing_logic == 'priority':
                self.machine_idx = routing.priority(self.machine)
            elif self.routing_logic == 'first_possible':
                self.machine_idx = routing.first_possible(self.machine)
            else:
                self.machine_idx = 0 if (self.parts_sent_to_machine == 0) or (
                            self.machine_idx == self.machine_num - 1) else self.machine_idx + 1

            # 기계로 Part 할당
            self.machine[self.machine_idx].machine.put(part)
            self.parts_sent_to_machine += 1

            # finish delaying of pre-process
            if (len(self.buffer_to_machine.items) < self.buffer_to_machine.capacity) and (len(self.waiting_pre_process) > 0):
                self.waiting_pre_process.popitem(last=False)[1].succeed()  # delay = (part_id, event)

    # Out-Buffer / Put Part into Next Process
    def to_process(self):
        while True:
            part = yield self.buffer_to_process.get()

            # next process
            step = 1
            next_process_name = part.data[(part.step + step, 'process')]
            next_process = self.model[next_process_name]
            if next_process.__class__.__name__ == 'Process':
                # buffer's capacity of next process is full -> have to delay
                if len(next_process.buffer_to_machine.items) == next_process.buffer_to_machine.capacity:
                    next_process.waiting_pre_process[part.id] = self.env.event()
                    self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Delay for Next Process")
                    yield next_process.waiting_pre_process[part.id]
                    self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Process to Process")

                else:
                    next_process.buffer_to_machine.put(part)
                    self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Process to Process")
            else:  # next_process == Sink
                next_process.put(part)
                self.monitor.record(self.env.now, self.name, None, part_id=part.id, event="Process to Sink")

            part.step += step
            self.parts_sent += 1

            if (len(self.buffer_to_process.items) < self.buffer_to_process.capacity) and (len(self.waiting_machine) > 0):
                self.waiting_machine.popitem(last=False)[1].succeed()  # delay = (part_id, event)


class Machine(object):
    def __init__(self, env, name, process_name, process_time, priority, out, waiting, monitor, MTTF, MTTR,
                 initial_broken_delay):
        # input data
        self.env = env
        self.name = name
        self.process_name = process_name
        self.process_time = process_time
        self.priority = priority
        self.out = out
        self.waiting = waiting
        self.monitor = monitor
        self.MTTR = MTTR
        self.MTTF = MTTF
        self.initial_broken_delay = initial_broken_delay

        # variable defined in class
        self.machine = simpy.Store(env)
        self.working_start = 0.0
        self.total_time = 0.0
        self.total_working_time = 0.0
        self.working = False  # whether machine's worked(True) or idled(False)
        self.broken = False  # whether machine is broken or not
        self.unbroken_start = 0.0
        self.planned_proc_time = 0.0

        # broke and re-running
        self.residual_time = 0.0
        self.broken_start = 0.0
        if self.MTTF is not None:
            mttf_time = self.MTTF if type(self.MTTF) == float else self.MTTF()
            self.broken_start = self.unbroken_start + mttf_time
        # get run functions in class
        self.action = env.process(self.work())

    def work(self):
        while True:
            self.broken = True
            part = yield self.machine.get()
            self.working = True
            # process_time
            if self.process_time == None:  # part에 process_time이 미리 주어지는 경우
                proc_time = part.data[(part.step, "process_time")]
            else:  # service time이 정해진 경우 --> 1) fixed time / 2) Stochastic-time
                proc_time = self.process_time if type(self.process_time) == float else self.process_time()
            self.planned_proc_time = proc_time

            while proc_time:
                if self.MTTF is not None:
                    self.env.process(self.break_machine())
                try:
                    self.broken = False
                    ## working start
                    self.monitor.record(self.env.now, self.process_name, self.name, part_id=part.id, event="Work Start")
                    self.working_start = self.env.now
                    yield self.env.timeout(proc_time)

                    ## working finish
                    self.monitor.record(self.env.now, self.process_name, self.name, part_id=part.id, event="Work Finish")
                    self.total_working_time += self.env.now - self.working_start
                    self.broken = True
                    proc_time = 0.0

                except simpy.Interrupt:
                    self.broken = True
                    self.monitor.record(self.env.now, self.process_name, self.name, part_id=part.id,
                                        event="Machine Broken")
                    print('{0} is broken at '.format(self.name), self.env.now)
                    proc_time -= self.env.now - self.working_start
                    if self.MTTR is not None:
                        repair_time = self.MTTR if type(self.MTTR) == float else self.MTTR()
                        yield self.env.timeout(repair_time)
                        self.unbroken_start = self.env.now
                    self.monitor.record(self.env.now, self.process_name, self.name, part_id=part.id,
                                        event="machine_rerunning")
                    print(self.name, 'is solved at ', self.env.now)
                    self.broken = False

                    mttf_time = self.MTTF if type(self.MTTF) == float else self.MTTF()
                    self.broken_start = self.unbroken_start + mttf_time

            self.working = False

            # Part transfer to Out Buffer
            self.out.put(part)

            self.total_time += self.env.now - self.working_start

    def break_machine(self):
        if (self.working_start == 0.0) and (self.initial_broken_delay is not None):
            initial_delay = self.initial_broken_delay if type(self.initial_broken_delay) == float else self.initial_broken_delay()
            yield self.env.timeout(initial_delay)
        residual_time = self.broken_start - self.working_start
        if (residual_time > 0) and (residual_time < self.planned_proc_time):
            yield self.env.timeout(residual_time)
            self.action.interrupt()
        else:
            return


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


class Routing(object):
    def __init__(self, priority=None):
        self.idx_priority = np.array(priority)

    def priority(self, server_list):
        i = min(self.idx_priority)
        idx = 0
        while i <= max(self.idx_priority):
            min_idx = np.argwhere(self.idx_priority == i)  # priority가 작은 숫자의 index부터 추출
            idx_min_list = min_idx.flatten().tolist()
            # 해당 index list에서 machine이 idling인 index만 추출
            idx_list = list(filter(lambda j: (server_list[j].working == False), idx_min_list))
            if len(idx_list) > 0:  # 만약 priority가 높은 machine 중 idle 상태에 있는 machine이 존재한다면
                idx = random.choice(idx_list)
                break
            else:  # 만약 idle 상태에 있는 machine이 존재하지 않는다면
                if i == max(self.idx_priority):  # 그 중 모든 priority에 대해 machine이 가동중이라면
                    idx = random.choice([j for j in range(len(self.idx_priority))])  # 그냥 무작위 배정
                    # idx = None
                    break
                else:
                    i += 1  # 다음 priority에 대하여 따져봄
        return idx

    def first_possible(self, server_list):
        idx_possible = random.choice([j for j in range(len(server_list))])  # random index로 초기화 - 모든 서버가 가동중일 때, 서버에 random하게 파트 할당
        for i in range(len(server_list)):
            if server_list[i].working is False:  # 만약 미가동중인 server가 존재할 경우, 해당 서버에 part 할당
                idx_possible = i
                break
        return idx_possible
