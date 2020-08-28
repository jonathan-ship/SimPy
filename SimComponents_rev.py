import simpy
import random
import os
from collections import deque
import pandas as pd
import numpy as np

from PostProcessing_rev import *


save_path = './result'
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
    def __init__(self, env, name, block_data, process_dict, monitor):
        self.env = env
        self.name = name
        self.block_data = block_data
        self.process_dict = process_dict
        self.Monitor = monitor

        self.action = env.process(self.run())
        self.parts_sent = 0
        self.flag = False

    def run(self):
        while True:
            # block_data로부터 part 정보 읽어주기
            part_id, data = self.block_data.index[self.parts_sent], self.block_data.iloc[self.parts_sent]

            # Part class로 modeling
            part = Part(part_id, data)

            if self.parts_sent != 0:
                IAT = part.data[(0, 'start_time')] - self.env.now
                if IAT > 0:
                    yield self.env.timeout(part.data[(0, 'start_time')] - self.env.now)

            # record: part_created
            self.Monitor.record(self.env.now, self.name, None, part_id=part.id, event="part_created")

            # next process
            next_process = part.data[(part.step, 'process')]

            next_server, next_queue = self.process_dict[next_process].get_num_of_part()
            if next_server + next_queue >= self.process_dict[next_process].qlimit:
                self.process_dict[next_process].waiting[part.id] = self.env.event()
                self.process_dict[next_process].delay_part_id.append(part.id)
                self.Monitor.record(self.env.now, self.name, None, part_id=part.id, event="delay_start")

                yield self.process_dict[next_process].waiting[part.id]
                self.Monitor.record(self.env.now, self.name, None, part_id=part.id, event="delay_finish")

            # record: part_transferred
            self.Monitor.record(self.env.now, self.name, None, part_id=part.id, event="part_transferred")

            self.process_dict[next_process].put(part)
            self.parts_sent += 1

            if self.parts_sent == len(self.block_data):
                print("all parts are sent at : ", self.env.now)
                break


class Process_without_subprocess(object):
    def __init__(self, env, name, server_num, process_dict, monitor, qlimit=float('inf')):
        self.env = env
        self.name = name
        self.server_num = server_num
        self.process_dict = process_dict
        self.Monitor = monitor
        self.qlimit = qlimit

        self.server = [None for _ in range(server_num)]
        self.queue = deque([])
        self.waiting = {}
        self.delay_part_id = []
        self.parts_rec = 0
        self.parts_sent = 0
        self.flag = False
        self.len_of_server = []

    def run(self, part, server_id):
        # record: work_start
        self.Monitor.record(self.env.now, self.name, '{0}_{1}'.format(self.name, server_id), part_id=part.id, event="work_start")
        # work start
        proc_time = part.data[(part.step, 'process_time')]
        yield self.env.timeout(proc_time)

        # record: work_finish
        self.Monitor.record(self.env.now, self.name, '{0}_{1}'.format(self.name, server_id), part_id=part.id, event="work_finish")

        # next process
        next_process = part.data[(part.step + 1, 'process')]

        if self.process_dict[next_process].__class__.__name__ == 'Process':
            # lag: 후행공정 시작시간 - 선행공정 종료시간
            lag = part.data[(part.step + 1, 'start_time')] - self.env.now
            if lag > 0:
                yield self.env.timeout(lag)

            # 대기 event 발생
            if len(self.process_dict[next_process].queue) + (self.process_dict[next_process].server_num - self.process_dict[next_process].server.count(None)) >= self.process_dict[next_process].qlimit:
                self.process_dict[next_process].waiting[part.id] = self.env.event()
                self.process_dict[next_process].delay_part_id.append(part.id)
                # record: delay_start
                self.Monitor.record(self.env.now, self.name, '{0}_{1}'.format(self.name, server_id), part_id=part.id, event="delay_start")

                yield self.process_dict[next_process].waiting[part.id]
                self.Monitor.record(self.env.now, self.name, '{0}_{1}'.format(self.name, server_id), part_id=part.id,
                                    event="delay_finish")

        # record: part_transferred
        self.Monitor.record(self.env.now, self.name, '{0}_{1}'.format(self.name, server_id), part_id=part.id, event="part_transferred")
        # part_transferred
        self.process_dict[next_process].put(part)
        part.step += 1
        self.parts_sent += 1

        if len(self.queue) > 0:
            part = self.queue.popleft()
            self.server[server_id] = self.env.process(self.run(part, server_id))
            # record: queue_released
            self.Monitor.record(self.env.now, self.name, None, part_id=part.id, event="queue_released")
        else:
            self.server[server_id] = None

        # 대기 종료
        server, queue = self.get_num_of_part()
        if server + queue < self.qlimit and len(self.waiting) > 0:
            delay_part = self.delay_part_id.pop(0)
            self.waiting.pop(delay_part).succeed()

    def put(self, part):
        self.parts_rec += 1
        if self.server.count(None) != 0:  # server에 자리가 있으면
            self.server[self.server.index(None)] = self.env.process(self.run(part, self.server.index(None)))
        else:  # server가 다 차 있으면
            self.queue.append(part)
            # record: queue_entered
            self.Monitor.record(self.env.now, self.name, None, part_id=part.id,  event="queue_entered")
        self.len_of_server.append(self.server_num - self.server.count(None))

    def get_num_of_part(self):
        queue = len(self.queue)
        server = self.server_num - self.server.count(None)

        return server, queue


class Process(object):
    def __init__(self, env, name, server_num, process_dict, monitor, process_time=None, qlimit=float('inf'), routing_logic="cyclic"):
        self.env = env
        self.name = name
        self.server_process_time = process_time[self.name] if process_time is not None else [None for _ in range(server_num)]
        self.server_num = server_num
        self.Monitor = monitor
        self.process_dict = process_dict
        self.server = [SubProcess(env, self.name, '{0}_{1}'.format(self.name, i), process_dict, self.server_process_time[i], self.Monitor) for i in range(server_num)]
        self.qlimit = qlimit
        self.routing_logic = routing_logic

        self.parts_sent = 0
        self.server_idx = 0
        self.waiting = {}
        self.delay_part_id = []

    def put(self, part):
        # Routing
        routing = Routing(self.server)
        if self.routing_logic == "least_utilized":  # routing logic = least utilized
            self.server_idx = routing.most_unutilized()
        elif self.routing_logic == "first_possible":  # routing_logic = first possible
            self.server_idx = routing.first_possible()
        else:  # routing logic = cyclic
            self.server_idx = 0 if (self.parts_sent == 0) or (self.server_idx == self.server_num-1) else self.server_idx + 1

        # lag: 현행공정 계획된 시작시간 - 현재 시각
        # if part.data[(part.step + step, 'start_time')] and process_from != 'Source':
        #     lag = part.data[(part.step + step, 'start_time')] - self.env.now
        #     if lag > 0:
        #         yield self.env.timeout(lag)

        # # delay start
        # server, queue = self.get_num_of_part()
        # if queue + server >= self.qlimit:
        #     self.server[self.server_idx].waiting.append(self.env.event())
        #     # record: delay_start
        #     self.Monitor.record(self.env.now, process_from, subprocess_from, part_id=part.id, event="delay_start")
        #
        #     yield self.server[self.server_idx].waiting[-1]
        #     # record: delay_finish
        #     self.Monitor.record(self.env.now, process_from, subprocess_from, part_id=part.id, event="delay_finish")

        # record: part_transferred
        # self.Monitor.record(self.env.now, process_from, subprocess_from, part_id=part.id, event="part_transferred")
        self.Monitor.record(self.env.now, self.name, self.server[self.server_idx].name, part_id=part.id, event="queue_entered")
        self.server[self.server_idx].sub_queue.put(part)

    def get_num_of_part(self):
        server_num = 0
        queue = 0
        for i in range(self.server_num):
            subprocess = self.server[i]
            server_num += 1 if subprocess.flag == True else 0
            queue += len(subprocess.sub_queue.items)

        return server_num, queue


class SubProcess(object):
    def __init__(self, env, process_name, server_name, process_dict, process_time, monitor):
        self.env = env
        self.process_name = process_name  # Process 이름
        self.name = server_name  # 해당 SubProcess의 id
        self.process_dict = process_dict
        self.process_time = process_time
        self.Monitor = monitor

        # SubProcess 실행
        self.action = env.process(self.run())
        self.sub_queue = simpy.Store(env)
        self.flag = False  # SubProcess의 작업 여부
        self.part = None
        self.working_start = 0.0
        self.total_time = 0.0
        self.working_time = 0.0

    def run(self):
        while True:
            # queue로부터 part 가져오기
            self.part = yield self.sub_queue.get()
            start_total_time = self.env.now
            self.Monitor.record(self.env.now, self.process_name, self.name, part_id=self.part.id, event="queue_released")
            self.flag = True

            # record: work_start
            self.Monitor.record(self.env.now, self.process_name, self.name, part_id=self.part.id, event="work_start")

            # work start
            self.working_start = self.env.now

            # process_time
            if self.process_time == None:  # part에 process_time이 미리 주어지는 경우
                proc_time = self.part.data[(self.part.step, "process_time")]
            else:  # service time이 정해진 경우 --> 1) fixed time / 2) Stochastic-time
                proc_time = self.process_time if type(self.process_time) == float else self.process_time()

            yield self.env.timeout(proc_time)

            # record: work_finish
            self.Monitor.record(self.env.now, self.process_name, self.name, part_id=self.part.id, event="work_finish")
            self.working_time += self.env.now - self.working_start

            step = 1
            while not self.part.data[(self.part.step + step, 'process_time')]:
                if self.part.data[(self.part.step + step, 'process')] != 'Sink':
                    step += 1
                else:
                    break

            # next process
            next_process = self.part.data[(self.part.step + step, 'process')]

            if self.process_dict[next_process].__class__.__name__ == 'Process':
                # lag: 후행공정 시작시간 - 선행공정 종료시간
                lag = self.part.data[(self.part.step + step, 'start_time')] - self.env.now
                if lag > 0:
                    yield self.env.timeout(lag)

                # delay start
                next_server, next_queue = self.process_dict[next_process].get_num_of_part()
                if next_server + next_queue >= self.process_dict[next_process].qlimit:
                    self.process_dict[next_process].waiting[self.part.id] = self.env.event()
                    self.process_dict[next_process].delay_part_id.append(self.part.id)
                    self.Monitor.record(self.env.now, self.process_name, self.name, part_id=self.part.id, event="delay_start")

                    yield self.process_dict[next_process].waiting[self.part.id]
                    self.Monitor.record(self.env.now, self.process_name, self.name, part_id=self.part.id, event="delay_finish")

                self.Monitor.record(self.env.now, self.process_name, self.name, part_id=self.part.id, event="part_transferred")
                self.process_dict[next_process].put(self.part)

            else:
                self.Monitor.record(self.env.now, self.process_name, self.name, part_id=self.part.id,
                                    event="part_transferred")
                self.process_dict[next_process].put(self.part)
            self.process_dict[self.process_name].parts_sent += 1

            self.flag = False

            self.part.step += step


            # delay finish
            server, queue = self.process_dict[self.process_name].get_num_of_part()
            if (server + queue < self.process_dict[self.process_name].qlimit) and (len(self.process_dict[self.process_name].waiting) > 0):
                delay_part = self.process_dict[self.process_name].delay_part_id.pop(0)
                self.process_dict[self.process_name].waiting.pop(delay_part).succeed()

            self.part = None

            self.total_time += self.env.now - start_total_time


class Sink(object):
    def __init__(self, env, name, monitor):
        self.env = env
        self.name = name
        self.Monitor = monitor

        self.parts_rec = 0
        self.last_arrival = 0.0

    def put(self, part):
        self.parts_rec += 1
        self.last_arrival = self.env.now
        self.Monitor.record(self.env.now, self.name, None, part_id=part.id, event="completed")


class Routing(object):
    def __init__(self, server):
        self.server = server  # routing logic을 적용할 server

    def most_unutilized(self):
        utilization_list = [(server.working_time/server.total_time if server.total_time != 0 else 0) for server in self.server]
        # utilization_list = self.server.apply(lambda x: x.working_time/x.total_time if x.total_time != 0 else 0)
        # for server in self.server:
        #     u = server.working_time / server.total_time if server.total_time !=0 else 0
        #     utilization_list.append(u)
        idx_min_list = np.argwhere(utilization_list == np.min(utilization_list))
        idx_min_list = idx_min_list.flatten().tolist()
        idx_min = random.choice(idx_min_list)
        return idx_min

    def first_possible(self):
        idx_possible = random.choice(range(len(self.server)))  # random index로 초기화 - 모든 서버가 가동중일 때, 서버에 random하게 파트 할당

        for i in range(len(self.server)):
            if self.server[i].flag == False:  # 만약 미가동중인 server가 존재할 경우, 해당 서버에 part 할당
                idx_possible = i
                break

        return idx_possible


class Monitor(object):
    def __init__(self, filename):
        self.filename = filename
        with open(self.filename, 'w', encoding='utf-8-sig') as f:
            f.write('Time,Event,Part,Process,SubProcess')

    def record(self, time, process, subprocess, part_id=None, event=None):
        with open(self.filename, 'a') as f:
            f.write('\n{0},{1},{2},{3},{4}'.format(time, event, part_id, process, subprocess))


