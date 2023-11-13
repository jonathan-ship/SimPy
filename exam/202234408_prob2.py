#!/usr/bin/env python
# coding: utf-8

# In[2]:


import simpy
import random


NUM_MACHINES = 10
WORKPIECES_PER_HOUR = 18
PROCESSING_TIME = 20 / 60  
BREAKDOWNS_PER_HOUR = 0.01
REPAIR_TIME = 2
DOWNTIME_COST = 100000
TECHNICIAN_WAGE = 30000 

# 초기 비용 가정
total_downtime_cost = 0
total_wage_cost = 0

class CuttingMachine(object):
    def __init__(self, env, num_machines):
        self.env = env
        self.machine = simpy.Resource(env, num_machines)

    def process_workpiece(self, workpiece):
        yield self.env.timeout(random.expovariate(1.0 / PROCESSING_TIME))

class Technician(object):
    def __init__(self, env, num_technicians):
        self.env = env
        self.technician = simpy.Resource(env, num_technicians)

    def repair_machine(self, machine):
        yield self.env.timeout(random.expovariate(1.0 / REPAIR_TIME))

def workpiece_arrivals(env, cutting_machine, technician):
    workpiece_count = 0
    while True:
        yield env.timeout(random.expovariate(WORKPIECES_PER_HOUR))
        workpiece_count += 1
        env.process(process_workpiece(env, cutting_machine, technician, workpiece_count))

def process_workpiece(env, cutting_machine, technician, workpiece_count):
    arrival_time = env.now
    with cutting_machine.machine.request() as request:
        yield request

        if random.random() < BREAKDOWNS_PER_HOUR * PROCESSING_TIME:
            env.process(break_down(env, cutting_machine, technician))

        yield env.process(cutting_machine.process_workpiece(workpiece_count))

def break_down(env, cutting_machine, technician):
    global total_downtime_cost, total_wage_cost
    with technician.technician.request() as request:
        yield request

        start_repair_time = env.now
        yield env.process(technician.repair_machine(cutting_machine))

        repair_time = env.now - start_repair_time
        total_downtime_cost += DOWNTIME_COST * repair_time
        total_wage_cost += TECHNICIAN_WAGE * repair_time

def run_simulation(num_technicians, run_time):
 
    env = simpy.Environment()
    global total_downtime_cost, total_wage_cost
    total_downtime_cost = 0
    total_wage_cost = 0

    # Create instances of CuttingMachine and Technician
    cutting_machine = CuttingMachine(env, NUM_MACHINES)
    technician = Technician(env, num_technicians)

    env.process(workpiece_arrivals(env, cutting_machine, technician))
    env.run(until=run_time)

    return total_downtime_cost, total_wage_cost

# 최적 기술자 수 산정
optimal_technicians = 0
min_total_cost = float('inf')

for num_technicians in range(1, 11):
    total_downtime_cost, total_wage_cost = run_simulation(num_technicians, 24 * 60)  # 60 days
    total_cost = total_downtime_cost + total_wage_cost
    print(f"기술자 수: {num_technicians}, 총 비용: {total_cost}")

    if total_cost < min_total_cost:
        min_total_cost = total_cost
        optimal_technicians = num_technicians

print(f"최적의 기술자 수: {optimal_technicians}, 최소 총 비용: {min_total_cost}")


# In[ ]:




