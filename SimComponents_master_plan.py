'''
3월 내 SimComponents와 통합 예정
'''

import simpy
from collections import deque, OrderedDict


class DataframePart(object):

    def __init__(self, time, block_data, id, data_num, src="a", dst="z", flow_id=0):
        self.time = time
        self.project = block_data[0]
        self.location_code = block_data[1]
        self.activity_data = block_data[2]
        self.simulation_data = OrderedDict()
        self.id = id
        self.src = src
        self.dst = dst
        self.flow_id = flow_id
        self.data_num = data_num

    def __repr__(self):
        return "id: {}, src: {}, time: {}".format(self.id, self.src, self.time)


class DataframeSource(object):

    def __init__(self, env, id, block_data, process_dict, data_num):
        self.id = id
        self.env = env
        self.block_data = block_data
        self.parts_sent = 0
        self.process_dict = process_dict
        self.action = env.process(self.run())
        self.data_num = data_num

    def run(self):
        while True:
            temp = next(self.block_data)
            p = DataframePart(self.env.now, temp, self.parts_sent, self.data_num,src=self.id)

            idx = list(p.activity_data.keys())[0]
            yield self.env.timeout(temp[-1][idx][0] - self.env.now)

            if len(self.process_dict[idx].queue) + self.process_dict[idx].server_num - self.process_dict[idx].server.count(None) >= self.process_dict[idx].qlimit:
                self.process_dict[idx].waiting.append(self.env.event())
                yield self.process_dict[idx].waiting[-1]

            self.parts_sent += 1
            self.process_dict[idx].put(p)

            if self.parts_sent == self.data_num:
                print('all parts are sent')
                break


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
        self.block_project_sim = {}

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

            if not part.project in list(self.block_project_sim.keys()):
                self.block_project_sim[part.project] = {}
            self.block_project_sim[part.project][part.location_code] = part.simulation_data


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
        self.qlimit = qlimit
        self.flag = False
        self.process_dict = process_dict
        self.out = None
        self.working_time = 0.0
        self.process_start = 0.0
        self.process_finish = 0.0


    def run(self, part, server_id):
        self.process_start = self.env.now if self.parts_rec == 0 else self.process_start
        proc_time = part.activity_data[self.name][1]
        start_time = self.env.now
        part.simulation_data[self.name] = [start_time]

        yield self.env.timeout(proc_time)
        self.working_time += self.env.now - start_time
        part.simulation_data[self.name].append(self.working_time)

        idx = list(part.activity_data.keys()).index(self.name)

        '''
        if msg.activity_data[next_process][1] < 0:
            idx += 1
        '''
        if idx != len(part.activity_data) - 1:
            next_process = list(part.activity_data.keys())[idx + 1]
            lag = part.activity_data[next_process][0] - self.env.now
            if lag > 0:
                yield self.env.timeout(lag)
            if len(self.process_dict[next_process].queue) + (self.process_dict[next_process].server_num - self.process_dict[next_process].server.count(None)) \
                    >= self.process_dict[next_process].qlimit:
                self.process_dict[next_process].waiting.append(self.env.event())
                yield self.process_dict[next_process].wait1[-1]

            self.process_dict[next_process].put(part)
        else:
            self.process_dict['Sink'].put(part)

        self.parts_sent += 1
        self.process_finish = self.env.now

        if len(self.queue) > 0:
            self.server[server_id] = self.env.process(self.run(self.queue.popleft(), server_id))
        else:
            self.server[server_id] = None

        if len(self.queue) + (self.server_num - self.server.count(None)) < self.qlimit and len(self.waiting) > 0:
            self.waiting.popleft().succeed()

        if self.parts_sent == part.data_num:
            self.flag = True

    def put(self, part):
        self.parts_rec += 1
        if self.server.count(None) != 0:
            self.server[self.server.index(None)] = self.env.process(self.run(part, self.server.index(None)))
        else:
            self.queue.append(part)


class Monitor(object):

    def __init__(self, env, port, dist):
        self.port = port
        self.env = env
        self.dist = dist
        self.M = [0]
        self.time = [0.0]
        self.WIP = [0]
        self.arrival_rate = [0]
        self.throughput = [0]
        self.action = env.process(self.run())
        self.parts_rec = 0
        self.parts_sent = 0

    def run(self):
        while True:
            #yield self.env.timeout(self.dist())
            yield self.env.timeout(self.dist)
            self.time.append(self.env.now)

            self.arrival_rate.append((self.port.parts_rec - self.parts_rec) / (self.time[-1] - self.time[-2]))
            self.throughput.append((self.port.parts_sent - self.parts_sent)/ (self.time[-1] - self.time[-2]))
            self.parts_rec = self.port.parts_rec
            self.parts_sent = self.port.parts_sent

            self.WIP.append(len(self.port.queue))
            self.M.append(self.port.server_num - self.port.server.count(None))

            if self.port.flag:
                break
