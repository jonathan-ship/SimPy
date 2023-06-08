#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import simpy

# 시뮬레이션 시간 설정
SIM_TIME = 1000000

# 각 공정의 평균 처리 시간 설정
PROCESS_TIME_1 = 1 / 2.4
PROCESS_TIME_2 = 1 / 2.4

class Process(object):
    def __init__(self, env, process_time):
        self.env = env
        self.machine = simpy.Resource(env, capacity=1)
        self.process_time = process_time

    def work(self):
        yield self.env.timeout(self.process_time)

def worker(env, process):
    while True:
        with process.machine.request() as req:
            yield req
            yield env.process(process.work())

# 시뮬레이션 환경 생성
env = simpy.Environment()

# 두 공정 생성
process1 = Process(env, PROCESS_TIME_1)
process2 = Process(env, PROCESS_TIME_2)

# 각 공정에 대한 작업자 생성
env.process(worker(env, process1))
env.process(worker(env, process2))

# 시뮬레이션 실행
env.run(until=SIM_TIME)


# In[ ]:




