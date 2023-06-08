# incomplete :(

import simpy
import random
import numpy as np

NUM_MACHINE_1 = 1
arrival_rate = 2.4  # per hour
c_a1 = 1.0
service_time_1 = 19  # minutes
c_01 = 0.5
MTBF_1 = 48 * 60  # minutes
MTTR_1 = 8 * 60  # minutes (exponential distribution)

NUM_MACHINE_2 = 1
service_time_2 = 22  # minutes
c_02 = 1.0
MTBF_2 = 3.3 * 60  # minutes
MTTR_2 = 10  # minutes (exponential distribution)

RANDOM_SEED = 42
SIM_TIME = 24 * 60  # minutes


def time_to_failure(MTBF):
    time = np.random.exponential(MTBF)
    if time < 0:
        time = 0.01
    return time


def time_per_part(mean, sigma):
    """Return actual processing time for a concrete part."""
    time = np.random.normal(mean, sigma)
    if time < 0:
        time = 0.01
    return time


def time_to_repair(MTTR):
    time = np.random.exponential(MTTR)
    if time < 0:
        time = 0.01
    return time


def time_to_arrive(mean, sigma):
    time = np.random.normal(mean, sigma)
    if time < 0:
        time = 0.01
    return time


class System(object):
    def __init__(self, env):
        self.env = env
        self.machine_1 = simpy.Resource(env, NUM_MACHINE_1)
        self.machine_2 = simpy.Resource(env, NUM_MACHINE_2)

        self.time_machine_1 = []
        self.time_queue_1 = []
        self.working_time_1 = []
        self.customer_queue_1 = 0
        self.customer_machine_1 = 0

        self.time_machine_2 = []
        self.time_queue_2 = []
        self.working_time_2 = []
        self.customer_queue_2 = 0
        self.customer_machine_2 = 0

        self.process = env.process(self.arrive())
        env.process(self.break_machine_1())
        env.process(self.break_machine_2())

        # for failure
        self.broken_1 = False
        self.broken_2 = False

    def arrive(self):
        i = 0
        while True:
            c = self.customer("Customer %d" % i)
            self.env.process(c)
            mean = 60 / arrival_rate
            sigma = c_a1 * mean
            arrival_time = time_to_arrive(mean, sigma)
            yield self.env.timeout(arrival_time)
            i += 1

    def customer(self, name):
        arrival = self.env.now
        print('%7.4f %s: Here I am' % (arrival, name))
        with self.machine_1.request() as req:
            yield req
            start = self.env.now
            self.customer_machine_1 += 1
            wait = start - arrival
            print('%7.4f %s: Waited at machine 1 %6.3f' % (self.env.now, name, wait))
            if wait > 0:
                self.customer_queue_1 += 1
            service_time = time_per_part(service_time_1, c_01 * service_time_1)
            while service_time:
                try:
                    # working time
                    yield self.env.timeout(service_time)
                    service_time = 0
                except simpy.Interrupt:
                    self.broken_1 = True
                    service_time -= self.env.now - start
                    yield self.env.timeout(time_to_repair(MTTR_1))
                    self.broken_1 = False

            finish = self.env.now

            print('%7.4f %s: Finished at machine 1' % (finish, name))

            self.customer_queue_1 -= 1
            self.customer_machine_1 -= 1
            self.time_machine_1.append(finish - arrival)
            self.working_time_1.append(finish - start)
            self.time_queue_1.append(wait)

        # After machine 1 is finished it goes into machine 2
        with self.machine_2.request() as req:
            yield req
            start = self.env.now
            self.customer_machine_2 += 1
            wait = start - arrival
            print('%7.4f %s: Waited at machine 2 %6.3f' % (self.env.now, name, wait))
            if wait > 0:
                self.customer_queue_2 += 1

            service_time = time_per_part(service_time_2, c_02 * service_time_2)
            while service_time:
                try:
                    # working time
                    yield self.env.timeout(service_time)
                    service_time = 0
                except simpy.Interrupt:
                    self.broken_2 = True
                    service_time -= self.env.now - start
                    yield self.env.timeout(time_to_repair(MTTR_2))
                    self.broken_2 = False

            finish = self.env.now

            print('%7.4f %s: Finished at machine 2' % (finish, name))

            self.customer_queue_2 -= 1
            self.time_machine_2.append(finish - arrival)
            self.working_time_2.append(finish - start)
            self.time_queue_2.append(wait)

    def break_machine_1(self):
        while True:
            yield self.env.timeout(time_to_failure(MTBF_1))
            if not self.broken_1:
                self.process.interrupt()

    def break_machine_2(self):
        while True:
            yield self.env.timeout(time_to_failure(MTBF_2))
            if not self.broken_2:
                self.process.interrupt()


def main():
    print('Problem 1')
    np.random.seed(RANDOM_SEED)
    env = simpy.Environment()

    # Start processes and run
    system = System(env)
    env.run(until=SIM_TIME)

    print('Average time in queue 1: %6.3f' % np.mean(system.time_queue_1))
    print('Average time in machine 1: %6.3f' % np.mean(system.time_machine_1))
    print('Average time in queue 2: %6.3f' % np.mean(system.time_queue_2))
    print('Average time in machine 2: %6.3f' % np.mean(system.time_machine_2))
    print('Average time in system: %6.3f' % np.mean(
        system.time_queue_1 + system.time_queue_2 + system.time_machine_1 + system.time_machine_2))

    print('Average number of customers in queue 1: %6.3f' % np.mean(system.customer_queue_1))
    print('Average number of customers in machine 1: %6.3f' % np.mean(system.customer_machine_1))
    print('Average number of customers in queue 2: %6.3f' % np.mean(system.customer_queue_2))
    print('Average number of customers in machine 2: %6.3f' % np.mean(system.customer_machine_2))

    print('Average number of customers in system: %6.3f' % np.mean(
        system.customer_queue_1 + system.customer_queue_2 + system.customer_machine_1 + system.customer_machine_2))


    print("Analytic results")
    print("WIP_q2 = 36.056")


if __name__ == '__main__':
    main()
