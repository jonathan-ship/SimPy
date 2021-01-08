import simpy
import random
import os
from collections import deque, namedtuple
import pandas as pd
import numpy as np

save_path = '../result'
if not os.path.exists(save_path):
    os.makedirs(save_path)


class Resource(object):
    def __init__(self, env, tp_info, wf_info, model, monitor):
        self.env = env
        self.model = model
        self.Monitor = monitor

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
        self.Monitor.record(self.env.now, process_requesting, None, part_id=part.id, event="tp_request")
        if len(self.tp_store.items) > 0:
            tp = yield self.tp_store.get(lambda item: item.capa == min_capa)
        else:
            tp_location_list = []
            for name in self.tp_location.keys():
                tp_location_list.append(self.tp_location[name][-1])
            location = random.choice(tp_location_list)
            tp = yield self.model[location].tp_store.get(lambda item: item.capa == min_capa)

        yield self.env.timeout(distance_to_requesting / tp.v_unloaded)
        self.Monitor.record(self.env.now, process_requesting, None, part_id=part.id, event="tp_arriving")
        yield self.env.timeout(distance_to_destination / tp.v_loaded)
        self.Monitor.record(self.env.now, process_requesting, None, part_id=part.id, event="tp_released")
        self.model[next_process].put(part)

        self.model[next_process].tp_store.put(tp)
        self.tp_location[tp.name].append(next_process)


class Part(object):
    def __init__(self, name, data):
        # 해당 Part의 이름
        self.id = name
        # 작업 시간 정보
        self.data = data
        # 작업을 완료한 공정의 수
        self.step = 0


class Source(object):
    def __init__(self, env, name, part_data, process_dict, monitor):
        self.env = env
        self.name = name
        self.part_data = part_data
        self.process_dict = process_dict
        self.Monitor = monitor

        self.action = env.process(self.run())
        self.parts_sent = 0
        self.flag = False

    def run(self):
        while True:
            # block_data로부터 part 정보 읽어주기
            part_id, data = self.part_data.index[self.parts_sent], self.part_data.iloc[self.parts_sent]

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

            if self.parts_sent == len(self.part_data):
                print("all parts are sent at : ", self.env.now)
                break


class Process(object):
    def __init__(self, env, name, server_num, process_dict, monitor, resource, process_time=None, qlimit=float('inf'), routing_logic="cyclic", priority=None):
        self.env = env
        self.name = name
        self.server_process_time = process_time[self.name] if process_time is not None else [None for _ in range(server_num)]  ## [5, 10, 15]
        self.server_num = server_num
        self.Monitor = monitor
        self.Resource = resource
        self.process_dict = process_dict
        self.server = [SubProcess(env, self.name, '{0}_{1}'.format(self.name, i), process_dict, self.server_process_time[i], self.Monitor) for i in range(server_num)]
        self.qlimit = qlimit
        self.routing_logic = routing_logic

        self.tp_store = simpy.FilterStore(env)  # transporter가 입고 - 출고 될 store
        self.parts_sent = 0
        self.server_idx = 0
        self.waiting = {}
        self.delay_part_id = []
        self.len_of_server = []

    def put(self, part):
        self.Monitor.record(self.env.now, self.name, None, part_id=part.id, event="Process_entered")
        # Routing
        routing = Routing(self.server)
        if self.routing_logic == "least_utilized":  # routing logic = least utilized
            self.server_idx = routing.least_utilized()
        elif self.routing_logic == "first_possible":  # routing_logic = first possible
            self.server_idx = routing.first_possible()
        else:  # routing logic = cyclic
            self.server_idx = 0 if (self.parts_sent == 0) or (self.server_idx == self.server_num-1) else self.server_idx + 1

        self.Monitor.record(self.env.now, self.name, None, part_id=part.id, event="routing_ended")

        # queue enter
        self.Monitor.record(self.env.now, self.name, self.server[self.server_idx].name, part_id=part.id, event="queue_entered")
        self.server[self.server_idx].sub_queue.put(part)
        self.len_of_server.append(self.server_idx)

    # 본 공정에 존재하는 가동 중인 서버 개수, queue에 존재하는 part의 개수 반환 --> qlimit와 비교하여 delay 여부 결정
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

                yield self.env.process(self.process_dict[self.process_name].Resource.request_tp(self.process_name, next_process, 0, 0, 100,
                                                                         part=self.part))
                self.Monitor.record(self.env.now, self.process_name, self.name, part_id=self.part.id,
                                    event="part_transferred")

            else:
                self.process_dict[next_process].put(self.part)
                self.Monitor.record(self.env.now, self.process_name, self.name, part_id=self.part.id,
                                    event="part_transferred")


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

        self.tp_store = simpy.FilterStore(env)  # transporter가 입고 - 출고 될 store
        self.parts_rec = 0
        self.last_arrival = 0.0

    def put(self, part):
        self.parts_rec += 1
        self.last_arrival = self.env.now
        self.Monitor.record(self.env.now, self.name, None, part_id=part.id, event="completed")


class Routing(object):
    def __init__(self, server):
        self.server = server  # routing logic을 적용할 server

    def least_utilized(self):
        utilization_list = [(server.working_time/server.total_time if server.total_time != 0 else 0) for server in self.server]
        idx_min_list = np.argwhere(utilization_list == np.min(utilization_list))
        idx_min_list = idx_min_list.flatten().tolist()
        idx_min = random.choice(idx_min_list)
        return idx_min

    def first_possible(self):
        idx_possible = random.choice(range(len(self.server)))  # random index로 초기화 - 모든 서버가 가동중일 때, 서버에 random하게 파트 할당
        for i in range(len(self.server)):
            if self.server[i].flag is False:  # 만약 미가동중인 server가 존재할 경우, 해당 서버에 part 할당
                idx_possible = i
                break
        return idx_possible


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

