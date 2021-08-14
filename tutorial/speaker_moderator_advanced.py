import simpy
from random import *

def speaker(env, i):
    try:
        talking_time = uniform(25, 35)
        print("{}th speaker's talking time is {:.2f} sec".format(i, talking_time))
        yield env.timeout(talking_time)
    except simpy.Interrupt as interrupt:
        print("{}th speaker's talking is interrupted at {:.2f} sec".format(i, env.now))
        print(interrupt.cause)

def moderator(env):
    for i in range(3):
        speaker_proc = env.process(speaker(env, i))
        results = yield speaker_proc | env.timeout(30)

        if speaker_proc not in results:
            speaker_proc.interrupt('No time left!')
        else:
            print("{:.2f} sec: speaker {} finished".format(env.now, i))

## Environment: The world that simulation is run
env = simpy.Environment()

## Passing generators to the env
env.process(moderator(env))

## simulation run.
## Run infinitely if time is not assigned as argument)
env.run(until=1000)
