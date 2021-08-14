import simpy

def speaker(env):
    yield env.timeout(30)
    return 'handout'

def moderator(env):
    for i in range(3):
        val = yield env.process(speaker(env))
        print("{:.2f} sec: speaker {} finished".format(env.now, i))

## Environment: The world that simulation is run
env = simpy.Environment()

## Passing generators to the env
env.process(moderator(env))

## simulation run.
## Run infinitely if time is not assigned as argument)
env.run(until=1000)
