import simpy
import random
import matplotlib.pyplot as plt


# Parameters
SIMULATION_TIME = 100000  # Simulation time in minutes
INTER_ARRIVAL_TIME = 3  # Average time between product arrivals in minutes

# Process 1
PROCESS1_TIME = 30
PROCESS1_MACHINE_NUM = 1.1

# Process 2
PROCESS2_TIME = 50
PROCESS2_MACHINE_NUM = 1.1

# Process 3
PROCESS3_TIME = 40
PROCESS3_MACHINE_NUM = 1.1


# Simulation logic
class Product:
    def __init__(self, id):
        self.id = id

def product_generator(env, process_queue):
    id = 0
    while True:
        yield env.timeout(random.expovariate(1.0/INTER_ARRIVAL_TIME))
        id += 1
        product = Product(id)
        product_queue.append(product)
        print(f"Product {id} arrived at time {env.now}")

def process1(env, product, machine):
    with machine.request() as request:
        yield request
        processing_time = random.expovariate(1.0/PROCESS1_TIME)
        yield env.timeout(processing_time)
        print(f"Product {product.id} passed process1 at time {env.now}")

def process2(env, product, machine):
    with machine.request() as request:
        yield request
        processing_time = random.expovariate(1.0/PROCESS2_TIME)
        yield env.timeout(processing_time)
        print(f"Product {product.id} passed process2 at time {env.now}")

def process3(env, product, machine):
    with machine.request() as request:
        yield request
        processing_time = random.expovariate(1.0/PROCESS3_TIME)
        yield env.timeout(processing_time)
        print(f"Product {product.id} passed process3 at time {env.now}")

def process_line(env, product_queue, machines, utilization):
    while True:
        if product_queue:
            product = product_queue.pop(0)
            print(f"Product {product.id} enters the process line at time {env.now}")
            env.process(process1(env, product, machines[0]))
            env.process(process2(env, product, machines[1]))
            env.process(process3(env, product, machines[2]))
        yield env.timeout(1)

        # Calculate resource utilization
        Process1_util = machines[0].count / PROCESS1_MACHINE_NUM
        Process2_util = machines[1].count / PROCESS2_MACHINE_NUM
        Process3_util = machines[2].count / PROCESS3_MACHINE_NUM

        print("utilization of process1 and number of machine are", Process1_util,"and",PROCESS1_MACHINE_NUM)
        print("utilization of process2 and number of machine are", Process2_util,"and",PROCESS2_MACHINE_NUM)
        print("utilization of process3 and number of machine are", Process3_util,"and",PROCESS3_MACHINE_NUM)


        # Update the utilization dictionary
        utilization["PROCESS1"].append(Process1_util)
        utilization["PROCESS2"].append(Process2_util)
        utilization["PROCESS3"].append(Process3_util)

# Run the simulation
env = simpy.Environment()
machines = [simpy.Resource(env) for _ in range(3)]
product_queue = []
utilization = {"PROCESS1": [], "PROCESS2": [], "PROCESS3": []}

env.process(product_generator(env, product_queue))
env.process(process_line(env, product_queue, machines,utilization))
#env.process(process1(env, product, machine))
#env.process(process2(env, product, machine))
env.run(until=SIMULATION_TIME)

# Plot the utilization
time = range(1, SIMULATION_TIME + 1)
for process, util_list in utilization.items():
    plt.plot(time[:len(util_list)], util_list, label=process)

plt.xlabel("Time")
plt.ylabel("Utilization")
plt.title("Resource Utilization")
plt.legend()
plt.show()
