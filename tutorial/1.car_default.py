import simpy
import numpy as np

## Park during 5 sec and drive during 2 sec
## car generator gets the env(simpy.environment) as argument, then make generator that perform env.timeout()
## Generator can have multible yield - Agents those have various state, then multiple generator should be implemented

def car(env):
    while True:
        print('Start parking at %5.1f' % env.now)
        parking_duration = 5
        #parking_duration = np.random.normal(5, 1)
        yield env.timeout(parking_duration)
        print('Stop  parking at %5.1f' % env.now)

        print('Start driving at %5.1f' % env.now)
        driving_duration = 2
        #trip_duration = np.random.normal(2, 1)
        yield env.timeout(driving_duration)
        print('Stop  driving at %5.1f' % env.now)

env = simpy.Environment()
env.process(car(env))
env.run(until=20)