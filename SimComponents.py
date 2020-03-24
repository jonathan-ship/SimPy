'''
data type = "gen" -> generator // data type = "df" -> dataframe
'''

import simpy
from collections import deque, OrderedDict


class Part(object):

    def __init__(self, time, data, id, data_num, src="a"):
        self.time = time
        self.id = id
        self.src = src
        self.data = data  # generator or dataframe에서 생성한 데이터
        self.data_num = data_num  # generator 용
        self.i = 0  ## 완료한 공정의 개수
        # self.simulation_data = OrderedDict()  # master_plan에만 적용

    def __repr__(self):
        return "id: {}, src: {}, time: {}".format(self.id, self.src, self.time)


class Source(object):

    def __init__(self, env, id, data_type, block_data, process_dict, data_num):
        self.env = env
        self.id = id
        self.data_type = data_type  # "df" : dataframe / "gen" : generator
        self.block_data = block_data  # "df" -> 전체 dataframe / "gen" -> generator 함수
        self.process_dict = process_dict
        self.data_num = data_num  # 전체 블록 갯수

        self.action = env.process(self.run())
        self.parts_sent = 0
        self.flag = False


    def run(self):
        while True:
            # data 받아오기
            if self.data_type == "gen":
                p = next(self.block_data)
            else:
                p = self.block_data.iloc[self.parts_sent]

            # part 생성
            part = Part(self.env.now, p, self.parts_sent, self.data_num, src=self.id)

            # IAT
            if self.parts_sent != 0:
                yield self.env.timeout(part.data[(0, 'start_time')] - self.env.now)

            # next process
            idx = part.data[(part.i, 'process')]
            if len(self.process_dict[idx].queue) + self.process_dict[idx].server_num - self.process_dict[idx].server.count(None) >= self.process_dict[idx].qlimit:
                self.process_dict[idx].waiting.append(self.env.event())
                yield self.process_dict[idx].waiting[-1]

            self.parts_sent += 1
            self.process_dict[idx].put(part)

            if self.parts_sent == self.data_num:
                print('all parts are sent')
                break

            if self.parts_sent == self.data_num:  # 해당 공정 종료
                self.flag = True


class Sink(object):

    def __init__(self, env, name, rec_lead_time=False, rec_arrivals=False, absolute_arrivals=False, selector=None):
        self.name = name
        self.env = env
        self.rec_lead_time = rec_lead_time
        self.rec_arrivals = rec_arrivals
        self.absolute_arrivals = absolute_arrivals
        self.selector = selector
        self.lead_time = []
        self.arrivals = []
        self.parts_rec = 0
        self.last_arrival = 0.0
        # self.block_project_sim = {}

    def put(self, part):
        if not self.selector or self.selector(part):
            now = self.env.now
            if self.rec_lead_time:
                self.lead_time.append(self.env.now - part.time)
            if self.rec_arrivals:
                if self.absolute_arrivals:
                    self.arrivals.append(now)
                else:
                    self.arrivals.append(now - self.last_arrival)
                self.last_arrival = now
            self.parts_rec += 1

            # self.block_project_sim[part.id] = part.simulation_data  # master_plan에만 적용


class Process(object):

    def __init__(self, env, name, server_num, process_dict, qlimit=None):
        self.name = name
        self.env = env
        self.server_num = server_num
        self.server = [None for _ in range(server_num)]
        self.queue = deque([])
        self.waiting = deque([])
        self.parts_rec = 0
        self.parts_sent = 0
        self.flag = False
        self.qlimit = qlimit
        # self.out = None
        self.working_time = 0.0
        self.process_start = 0.0
        self.process_finish = 0.0
        self.process_dict = process_dict

    def run(self, part, server_id):
        ## ??
        self.process_start = self.env.now if self.parts_rec == 0 else self.process_start
        start_time = self.env.now

        proc_time = part.data[(part.i, 'process_time')]
        yield self.env.timeout(proc_time)
        self.working_time += self.env.now - start_time

        # # master_plan에만 적용
        # part.simulation_data[self.name] = [start_time]
        # part.simulation_data[self.name].append(self.working_time)

        # next process
        next_process = part.data[(part.i + 1, 'process')]

        if self.process_dict[next_process].__class__.__name__ == 'Process':
            lag = part.data[(part.i + 1, 'start_time')] - self.env.now
            if lag > 0:
                yield self.env.timeout(lag)
            if len(self.process_dict[next_process].queue) + (self.process_dict[next_process].server_num - self.process_dict[next_process].server.count(None)) >= self.process_dict[next_process].qlimit:
                self.process_dict[next_process].waiting.append(self.env.event())
                yield self.process_dict[next_process].wait1[-1]

        self.process_dict[next_process].put(part)
        part.i += 1
        self.parts_sent += 1
        self.process_finish = self.env.now  # part가 해당 공정에서 out된 시각

        if len(self.queue) > 0:  ## ??
            self.server[server_id] = self.env.process(self.run(self.queue.popleft(), server_id))
        else:
            self.server[server_id] = None

        if len(self.queue) + (self.server_num - self.server.count(None)) < self.qlimit and len(self.waiting) > 0:
            self.waiting.popleft().succeed()

        if self.parts_sent == part.data_num:  # 해당 공정 종료
            self.flag = True

    def put(self, part):
        self.parts_rec += 1
        if self.server.count(None) != 0:  # server에 자리가 있으면
            self.server[self.server.index(None)] = self.env.process(self.run(part, self.server.index(None)))
        else:  # server가 다 차 있으면
            self.queue.append(part)


class Monitor(object):

    def __init__(self, env, port, dist):
        self.port = port
        self.env = env
        self.dist = dist
        self.u = 0
        self.M = [0]
        self.time = [0.0]
        self.WIP = [0]
        self.arrival_rate = [0]
        self.throughput = [0]
        self.action = env.process(self.run())
        self.parts_rec = 0
        self.parts_sent = 0
        self.parts_sent_list = []

    def run(self):
        while True:
            #yield self.env.timeout(self.dist())
            yield self.env.timeout(self.dist)
            self.time.append(self.env.now)

            # self.arrival_rate.append((self.port.parts_rec - self.parts_rec) / (self.time[-1] - self.time[-2]))
            self.arrival_rate.append((self.port.parts_rec - self.parts_rec))
            self.throughput.append((self.port.parts_sent - self.parts_sent)/ (self.time[-1] - self.time[-2]))
            self.parts_rec = self.port.parts_rec
            self.parts_sent = self.port.parts_sent

            self.WIP.append(len(self.port.queue))
            self.M.append(self.port.server_num - self.port.server.count(None))

            if self.port.flag:
                break