import simpy
import pandas as pd
from Postprocessing import Utilization

EVENT_TRACER = pd.DataFrame(columns={"PART", "EVENT", "TIME", "PROCESS", "SERVER_ID"})


class Part(object):
    def __init__(self, name, data):
        # 해당 Part의 이름
        self.id = name
        # 작업 시간 정보
        self.data = data
        # 작업을 완료한 공정의 수
        self.step = 0


class Source(object):
    def __init__(self):
        pass

    def run(self):
        pass

    def record(self, part, time, process, server_id=None, event=None):
        EVENT_TRACER.loc[len(EVENT_TRACER)] = [part, event, time, process, server_id]


class Process(object):
    def __init__(self):
        pass

    def routing(self):
        pass


class SubProcess(object):
    def __init__(self, server_id):
        pass

    def run(self, part):
        pass

    def record(self, part, time, process, server_id=None, event=None):
        EVENT_TRACER.loc[len(EVENT_TRACER)] = [part, event, time, process, server_id]


class Sink(object):
    def __init__(self):
        pass

    def put(self):
        pass