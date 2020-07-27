import simpy
import pandas as pd
import numpy as np

EVENT_TRACER = pd.DataFrame(columns={"PART", "TIME", "EVENT", "PROCESS", "SERVER_ID"})


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

        # delay start
        next_server, next_queue = self.process_dict[next_process].get_num_of_part()
        if next_queue + next_server >= self.process_dict[next_process].qlimit:
            self.process_dict[next_process].waiting.append(self.env.event())
            # record: delay_start
            record(self.env.now, self.name, event="delay_start")

            yield self.process_dict[next_process].waiting[-1]
            # delay_finish
            record(self.env.now, self.name, event="delay_start")

        # part transferred
        # record: part_transferred
        record(self.env.now, self.name, part_id=part.id, event="part_transferred")

        self.parts_sent += 1
        self.process_dict[next_process].put(part)


class Process(object):
    def __init__(self, env, name, server_num, process_dict, process_time=None, qlimit=None):
        self.env = env
        self.name = name
        self.server_process_time = process_time if process_time != None else [None for i in range(server_num)]
        self.process_dict = process_dict
        self.server_num = server_num
        self.server = [SubProcess(env, self.name, i, process_dict, self.server_process_time[i]) for i in
                       range(server_num)]
        self.qlimit = qlimit
        self.Routing = Routing(self.process_dict[self.name])

    def put(self, part, routing="cyclic"):
        # Routing
        server_idx = 0
        if routing == "most_unutilized":
            server_idx = self.Routing.most_unutilized()
        else:  # cyclic
            server_idx = server_idx + 1 if (server_idx < self.server_num - 1) & (server_idx != 0) else 0

        record(self.env.now, self.name, part_id=part.id, server_id=self.server[server_idx].id, event="queue_entered")
        self.server[server_idx].queue.put(part)


    def get_num_of_part(self):
        server_num = 0
        queue = 0
        for i in range(self.server_num):
            subprocess = self.server[i]
            server_num += 1 if subprocess.flag == True else 0
            queue += len(subprocess.queue.items)

        return server_num, queue


class SubProcess(object):
    def __init__(self, env, idx, process_name, process_dict, process_time):
        self.env = env
        self.process_name = process_name  # Process 이름
        self.id = process_name + '_' + str(idx)  # 해당 SubProcess의 id
        self.process_dict = process_dict
        self.process_time = process_time

        # SubProcess 실행
        self.action = env.process(self.run())
        self.queue = simpy.Store(self.env)
        self.waiting = []
        self.flag = False  # SubProcess의 작업 여부

    def run(self):
        # queue로부터 part 가져오기
        part = yield self.queue.get()
        self.flag = True
        # record: work_start
        record(self.env.now, self.process_name, part_id=part.id, server_id=self.id, event="work_start")

        # work start
        proc_time = self.process_time if self.process_time is not None else part.data[(part.step, "process_time")]
        yield self.env.timeout(proc_time)

        # record: work_finish
        record(self.env.now, self.process_name, part_id=part.id, server_id=self.id, event="work_finish")

        # next process
        next_process = part.data[(part.step + 1, 'process')]

        if self.process_dict[next_process].__class__.__name__ == 'Process':
            # lag: 후행공정 시작시간 - 선행공정 종료시간
            lag = part.data[(part.step + 1, 'start_time')] - self.env.now
            if lag > 0:
                yield self.env.timeout(lag)

        # delay start
        next_server, next_queue = self.process_dict[next_process].get_num_of_part()
        if next_queue + next_server >= self.process_dict[next_process].qlimit:
            self.process_dict[next_process].waiting.append(self.env.event())
            # record: delay_start
            record(self.env.now, self.process_name, server_id=self.id, event="delay_start")

            yield self.process_dict[next_process].waiting[-1]
            # record: delay_finish
            record(self.env.now, self.process_name, server_id=self.id, event="delay_finish")

        # record: part_transferred
        record(self.env.now, self.process_name, part_id=part.id, server_id=self.id, event="part_transferred")
        # part_transferred
        self.process_dict[next_process].put(part)
        part.step += 1
        self.flag = False

        # delay finish
        server, queue = self.process_dict[self.process_name].get_num_of_part()
        if server + queue < self.process_dict[self.process_name].qlimit:
            self.waiting[0].succeed()

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

    def most_unutilized(self):
        from PostProcessing_rev import Utilization
        utilization_list = [Utilization(EVENT_TRACER, self.process.process_dict, self.server[i].id, type="Server") for i
                            in range(self.server_num)]
        idx_min = np.argmin(utilization_list)
        return idx_min


def record(time, process, part_id=None, server_id=None, event=None):
    EVENT_TRACER.loc[len(EVENT_TRACER)] = [part_id, time, event, process, server_id]
