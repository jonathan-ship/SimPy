"""
Bank renege example

Covers:

- Resources: Resource
- Condition events

Scenario:
  A counter with a random service time and customers who renege. Based on the
  program bank08.py from TheBank tutorial of SimPy 2. (KGM)

"""
import random
import simpy
import numpy as np


RANDOM_SEED = 42
NEW_CUSTOMERS = 5  # Total number of customers
INTERVAL_CUSTOMERS = 10.0  # Generate new customers roughly every x seconds
MIN_PATIENCE = 1  # Min. customer patience
MAX_PATIENCE = 3  # Max. customer patience


def source(env, number, service_time, interval, counter):
    """Source generates customers randomly"""
    for i in range(number):
        c = customer(env, 'Customer%02d' % i, counter, time_in_bank=service_time)
        env.process(c)
        t = random.expovariate(1.0 / interval)
        yield env.timeout(t)


def customer(env, name, counter, time_in_bank):
    """Customer arrives, is served and leaves."""
    arrive = env.now
    print('%7.4f %s: Here I am' % (arrive, name))

    with counter.request() as req:
        patience = random.uniform(MIN_PATIENCE, MAX_PATIENCE)
        # Wait for the counter or abort at the end of our tether
        results = yield req | env.timeout(patience)

        wait = env.now - arrive

        if req in results:
            # We got to the counter
            print('%7.4f %s: Waited %6.3f' % (env.now, name, wait))

            tib = random.expovariate(1.0 / time_in_bank)
            yield env.timeout(tib)
            print('%7.4f %s: Finished' % (env.now, name))

        else:
            # We reneged
            print('%7.4f %s: RENEGED after %6.3f' % (env.now, name, wait))


def optimize(num_of_counters, service_time):
    num_of_counters_optimized = 0
    service_time_optimized = 0
    simulation_time = 0
    for i in num_of_counters:
        for j in service_time:
            env = simpy.Environment()
            counter = simpy.Resource(env, capacity=i)
            env.process(source(env, NEW_CUSTOMERS, j, INTERVAL_CUSTOMERS, counter))
            env.run()
            if abs(env.now - 200) < abs(simulation_time - 200):
                simulation_time = env.now
                num_of_counters_optimized = i
                service_time_optimized = j
    return num_of_counters_optimized, service_time_optimized, simulation_time


if __name__ == "__main__":
    print('Bank renege')
    random.seed(RANDOM_SEED)
    num_of_counters = np.arange(1, 6)
    service_time = np.arange(20, 31)
    num_of_counters_optimized, service_time_optimized, simulation_time \
        = optimize(num_of_counters, service_time)
    print("\n" + "==========" * 10)
    print("Results of Optimization")
    print("the number of counters opimized: {0}, service_time_optimized: {1} | simulation time: {2}"
          .format(num_of_counters_optimized, service_time_optimized, simulation_time))