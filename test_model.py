from SimComponents_V2 import *
import simpy

filepath = './result/event_log_test.csv'
env = simpy.Environment()
monitor = Monitor(filepath)

operation = dict()
operation['Ops1-1'] = Operation('Ops1-1', 5, ['M1','M2'])
operation['Ops1-2'] = Operation('Ops1-2', 5, ['M3','M4','M5'])
operation['Ops1-3'] = Operation('Ops1-3', 5, ['M3','M4','M5'])
operation['Ops2-1'] = Operation('Ops2-1', 5, ['M1','M2'])
operation['Ops2-2'] = Operation('Ops2-2', 5, ['M3','M4','M5'])
operation['Ops3-1'] = Operation('Ops3-1', 5, ['M3','M4','M5'])
operation['Ops3-2'] = Operation('Ops3-2', 5, ['M1','M2'])

model = dict()
model['M1'] = Process(env, 'M1', model, monitor, capacity=2, in_buffer=2, out_buffer=2)
model['M2'] = Process(env, 'M2', model, monitor, capacity=2, in_buffer=2, out_buffer=2)
model['M3'] = Process(env, 'M3', model, monitor, capacity=2, in_buffer=2, out_buffer=2)
model['M4'] = Process(env, 'M4', model, monitor, capacity=2, in_buffer=2, out_buffer=2)
model['M5'] = Process(env, 'M5', model, monitor, capacity=2, in_buffer=2, out_buffer=2)
model['Routing'] = Routing(env, model, monitor)
model['Sink'] = Sink(env, monitor)

jobtype1 = [operation['Ops1-1'], operation['Ops1-2'], operation['Ops1-3']]
jobtype2 = [operation['Ops2-1'], operation['Ops2-2']]
jobtype3 = [operation['Ops3-1'], operation['Ops3-2']]

source1 = Source(env, 'Source_jobtype1', model, monitor, jobtype=jobtype1, IAT=15)
source2 = Source(env, 'Source_jobtype2', model, monitor, jobtype=jobtype2, IAT=10)
source3 = Source(env, 'Source_jobtype3', model, monitor, jobtype=jobtype3, IAT=10)

env.run(until=1000)

monitor.save_event_tracer()