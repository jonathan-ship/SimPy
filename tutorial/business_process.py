import simpy
import numpy as np

## Let's assume a certain business process P, then P is composed of several activities.
## Each activity can have a constraint as resource (Resource entity is not treated in this example).
## Make a business process as a generator.
## Specific activity is performed.

def business_process(env, activity_lst):
    while True:
        for act in activity_lst:
            ## activity duration follows triangulat distribution
            print('start {} at {:6.2f}'.format(act, env.now))
            activity_time = np.random.triangular(left=3, right=10, mode=7)
            yield env.timeout(activity_time)
            print('end   {} at {:6.2f}'.format(act, env.now))

            ## Transfer activity to the next step require a certain amount of time
            activity_transfer_time = np.random.triangular(left=1, right=3, mode=2)
            yield env.timeout(activity_transfer_time)
        print("#" * 30)
        print("process end")
        ## return terminates simulation.
        return 'over'


## environment setting
env = simpy.Environment()

bp1 = business_process(env, activity_lst=["activity_{}".format(i) for i in range(1, 6)])
env.process(bp1)

## Since generator has a termination condition, the value passed to until in env.run(until=1000) becomes meaningless.
env.run(until=100)