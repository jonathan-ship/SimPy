import os
import simpy
import random
from postprocessing import Monitor


# Parameters
SIMULATION_TIME = 100  # Simulation time in seconds
INTER_ARRIVAL_TIME = 3  # Average time between product arrivals in minutes

# Process 1
PROCESS1_TIME = 2
PROCESS1_STD = 1
PROCESS1_VAR = PROCESS1_STD * PROCESS1_STD

# Process 2
PROCESS2_TIME = 1
PROCESS2_STD = 1.5
PROCESS2_VAR = PROCESS2_STD * PROCESS2_STD

# Simulation logic
class Product:
    def __init__(self, id):
        self.id = id

def product_generator(env, monitor, process_queue):
    id = 0
    while True:
        yield env.timeout(random.expovariate(1.0/INTER_ARRIVAL_TIME))
        id += 1
        product = Product(id)
        product_queue.append(product)
        monitor.record(id, env.now, "Product arrived")
        print(f"Product {id} arrived at time {env.now}")

def process1(env, product, machine):
    with machine.request() as request:
        yield request
        processing_time = max(0,random.normalvariate(PROCESS1_TIME,PROCESS1_STD))
        yield env.timeout(processing_time)
        #monitor.record(id, env.now, "passed process1")
        print(f"Product {product.id} passed process1 at time {env.now}")

def process2(env, product, machine):
    with machine.request() as request:
        yield request
        processing_time = max(0,random.normalvariate(PROCESS2_TIME,PROCESS2_STD))
        yield env.timeout(processing_time)
        #monitor.record(id, env.now, "passed process2")
        print(f"Product {product.id} passed process2 at time {env.now}")

def process_line(id,env, monitor,product_queue, machines):
    while True:
        if product_queue:
            product = product_queue.pop(0)
            monitor.record(id, env.now, "enters the process line at time")
            print(f"Product {product.id} enters the process line at time {env.now}")
            env.process(process1(env, product, machines[0]))
            env.process(process2(env, product, machines[1]))
        yield env.timeout(1)

# Run the simulation
if __name__ == "__main__":

    file_path = "./result/problem3"
    if not os.path.exists(file_path):
        os.makedirs(file_path)

    env = simpy.Environment()
    machines = [simpy.Resource(env) for _ in range(2)]
    product_queue = []
    monitor = Monitor()

    env.process(product_generator(env, monitor,product_queue))
    env.process(process_line(id,env, monitor, product_queue, machines))
    #env.process(process1(env, product, machine))
    #env.process(process2(env, product, machine))
    env.run(until=SIMULATION_TIME)

    monitor.save_file(file_path + "/log.csv")
