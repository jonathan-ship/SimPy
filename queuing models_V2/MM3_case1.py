from SimComponents_V2 import *
import simpy
import numpy as np
import random

np.random.seed(42)
random.seed(42)

filepath = '../result/event_log_MM3.csv'
env = simpy.Environment()
monitor = Monitor(filepath)

operation = dict()
operation['Ops1-1'] = Operation('Ops1-1', 'exponential(50)', ['M1'])


model = dict()
model['M1'] = Process(env, 'M1', model, monitor, capacity=3, in_buffer=0, out_buffer=0)
model['Routing'] = Routing(env, model, monitor)
model['Sink'] = Sink(env, monitor)

jobtype1 = [operation['Ops1-1']]


source = Source(env, 'Source_jobtype1', model, monitor, jobtype=jobtype1, IAT='exponential(20)')

env.run(until=100000)

monitor.save_event_tracer()


print('#' * 80)
print("Results of MM3 simulation")

print("Makespan : ", model['Sink'].last_arrival)
print("Makepart : ", model['Sink'].parts_rec)