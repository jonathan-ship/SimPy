import simpy
import pandas as pd
import numpy as np

EVENT_TRACER = pd.DataFrame(columns=["TIME", "EVENT", "PART", "PROCESS", "SERVER_ID"])


class Part(object):
    def __init__(self, name, data):
        # 해당 Part의 이름
        self.id = name
        # 작업 시간 정보
        self.data = data
        # 작업을 완료한 공정의 수
        self.step = 0


class Source(object):
    def __init__(self, env, name, block_data, process_dict):
        self.env = env
        self.name = name
        self.block_data = block_data
        self.process_dict = process_dict

        self.action = env.process(self.run())
        self.parts_sent = 0
        self.flag = False

    def run(self):
        while True:
            # block_data로부터 part 정보 읽어주기
            data = self.block_data.iloc[self.parts_sent]

            # Part class로 modeling
            part = Part(data["part"], data)

            if self.parts_sent != 0:
                IAT = part.data[(0, 'start_time')] - self.env.now
                if IAT > 0:
                    yield self.env.timeout(part.data[(0, 'start_time')] - self.env.now)

            # record: part_created
            record(self.env.now, self.name, part_id=part.id, event="part_created")

            # next process
            next_process = part.data[(part.step, 'process')]
            yield self.env.process(self.process_dict[next_process].put(part, self.name, None))
            self.parts_sent += 1
            # record: part_transferred
            record(self.env.now, self.name, part_id=part.id, event="part_transferred")

            if self.parts_sent == len(self.block_data):
                break


class Process(object):
    def __init__(self, env, name, server_num, process_dict, process_time=None, qlimit=float('inf'), routing_logic="cyclic"):
        self.env = env
        self.name = name
        self.server_process_time = process_time[self.name] if process_time is not None else [None for _ in range(server_num)]
        self.process_dict = process_dict
        self.server_num = server_num
        self.server = [SubProcess(env, self.name, '{0}_{1}'.format(self.name, i), process_dict, self.server_process_time[i]) for i in range(server_num)]
        self.qlimit = qlimit
        self.routing_logic = routing_logic

        self.parts_sent = 0
        self.server_idx = 0

    def put(self, part, process_from, server_from):
        if part.data[(part.step, 'process_time')]:  # process_time > 0 일 때
            # Routing
            routing = Routing(self.process_dict[self.name])
            if self.routing_logic == "most_unutilized":  # most_unutilized
                self.server_idx = routing.most_unutilized()
            else:
                self.server_idx = 0 if (self.parts_sent == 0) or (self.server_idx == self.server_num-1) else self.server_idx + 1

            # lag: 현행공정 계획된 시작시간 - 현재 시각
            if part.data[(part.step, 'start_time')]:
                lag = part.data[(part.step, 'start_time')] - self.env.now
                if lag > 0:
                    yield self.env.timeout(lag)

            # delay start
            server, queue = self.get_num_of_part()
            if queue + server >= self.qlimit:
                self.server[self.server_idx].waiting.append(self.env.event())
                # record: delay_start
                record(self.env.now, process_from, part_id=part.id, server_id=server_from, event="delay_start")

                yield self.server[self.server_idx].waiting[-1]
                # record: delay_finish
                record(self.env.now, process_from, part_id=part.id, server_id=server_from, event="delay_finish")

            record(self.env.now, self.name, part_id=part.id, server_id=self.server[self.server_idx].name, event="queue_entered")
            self.server[self.server_idx].sub_queue.put(part)
        else:
            next_process = part.data[(part.step + 1, 'process')]
            if self.process_dict[next_process].__class__.__name__ == 'Process':
                self.process_dict[next_process].put(part, process_from, server_from)
            else:
                self.process_dict[next_process].put(part)

    def get_num_of_part(self):
        server_num = 0
        queue = 0
        for i in range(self.server_num):
            subprocess = self.server[i]
            server_num += 1 if subprocess.flag == True else 0
            queue += len(subprocess.sub_queue.items)

        return server_num, queue


class SubProcess(object):
    def __init__(self, env, process_name, server_name, process_dict, process_time):
        self.env = env
        self.process_name = process_name  # Process 이름
        self.name = server_name  # 해당 SubProcess의 id
        self.process_dict = process_dict
        self.process_time = process_time

        # SubProcess 실행
        self.action = env.process(self.run())
        self.sub_queue = simpy.Store(env)
        self.waiting = []
        self.flag = False  # SubProcess의 작업 여부
        self.part = None
        self.working_start = 0.0

    def run(self):
        while True:
            # queue로부터 part 가져오기
            self.part = yield self.sub_queue.get()
            record(self.env.now, self.process_name, part_id=self.part.id, server_id=self.name, event="queue_released")
            self.process_dict[self.process_name].parts_sent += 1
            self.flag = True

            # record: work_start
            record(self.env.now, self.process_name, part_id=self.part.id, server_id=self.name, event="work_start")

            # work start
            self.working_start = self.env.now
            proc_time = self.process_time if self.process_time is not None else self.part.data[(self.part.step, "process_time")]
            yield self.env.timeout(proc_time)

            # record: work_finish
            record(self.env.now, self.process_name, part_id=self.part.id, server_id=self.name, event="work_finish")

            # next process
            self.part.step += 1
            next_process = self.part.data[(self.part.step, 'process')]
            if self.process_dict[next_process].__class__.__name__ == 'Process':
                yield self.env.process(self.process_dict[next_process].put(self.part, self.process_name, self.name))
            else:
                self.process_dict[next_process].put(self.part)
            self.process_dict[self.process_name].parts_sent += 1
            # record: part_transferred
            record(self.env.now, self.process_name, part_id=self.part.id, server_id=self.name, event="part_transferred")

            self.flag = False

            self.part = None

            # delay finish
            server, queue = self.process_dict[self.process_name].get_num_of_part()
            if (server + queue < self.process_dict[self.process_name].qlimit) and (len(self.waiting) > 0):
                self.waiting.pop(0).succeed()


class Sink(object):
    def __init__(self, env, name):
        self.name = name
        self.env = env
        self.parts_rec = 0
        self.last_arrival = 0.0

    def put(self, part):
        self.parts_rec += 1
        self.last_arrival = self.env.now


class Routing(object):
    def __init__(self, process):
        self.process = process  # routing logic을 적용할 process
        self.server = self.process.server
        self.server_num = self.process.server_num

    def most_unutilized(self):  ##
        from PostProcessing_rev import Utilization
        utilization_list = []
        for i in range(self.server_num):
            utilization = Utilization(EVENT_TRACER, self.process.process_dict, self.server[i].name, type="Server")
            server_utilization = utilization.utilization()
            utilization_list.append(server_utilization)
        idx_min = np.argmin(utilization_list)
        return idx_min


def record(time, process, part_id=None, server_id=None, event=None):
    EVENT_TRACER.loc[len(EVENT_TRACER)] = [time, event, part_id, process, server_id]


def return_event_tracer():
    return EVENT_TRACER
