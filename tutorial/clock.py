import simpy

## Generator with loop and yield
## Simpy uses generator basically,
## Generator can be assumed as commands list including yield
## yield: return something and hold

def clock(env, name, tick):
    while True:
        ## Once clock (kinds of generator) is called, following behavior is conducted
        print("{:.2f} sec: {} clock ticks".format(env.now, name))
        ## Hold (or consum time) during the time passed thru argument
        yield env.timeout(tick)

## Environment: The world that simulation is run
env = simpy.Environment()

## Following statements are passing generator (not function)
## Clock that rings every 0.5 sec
fast_clock = clock(env, '     fast', 0.5)
## Clock that rings every 1 sec
slow_clock = clock(env, '     slow', 1)
## Clock that rings every 0.1 sec
very_fast_clock = clock(env, 'very fast', 0.1)

## Passing these 3 generators to the env
env.process(fast_clock)
env.process(slow_clock)
env.process(very_fast_clock)

## simulation run.
## Run infinitely if time is not assigned as argument)
env.run(until=2)