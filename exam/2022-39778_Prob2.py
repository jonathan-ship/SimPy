import random
import numpy as np
import simpy

#Find Technicians Number
RANDOM_SEED = 42
AT_MEAN = 18 / 60      # Avg. arrival time in minutes, Exponential
PT_MEAN = 20.0         # Avg. processing time in minutes, Exponential
BREAK_MEAN = 0.01 / 60 # Avg. breakdown in minutes, Poisson
REPAIR_TIME = 60.0     # Time it takes to repair a machine in minutes, Exponential
LOSS = 100000 / 60     # Loss of breakdown in minutes
WAGE = 30000 / 60      # Wage of technicians in minutes
NUM_MACHINES = 10      # Number of machines in the machine shop
WEEKS = 4              # Simulation time in weeks
SIM_TIME = WEEKS * 7 * 24 * 60  # Simulation time in minutes
TECH_NO_INI = 1        # Initial technician number

def time_per_part():
    return random.expovariate(PT_MEAN)

def time_to_failure():
    return np.random.poisson(BREAK_MEAN)

class Machine(object):

    def __init__(self, env, name, repairman, AT_MEAN, REPAIR_TIME):
        self.env = env
        self.name = name
        self.parts_made = 0
        self.broken = False
        self.AT_MEAN = np.random.exponential(AT_MEAN)
        self.REPAIR_TIME = np.random.exponential(REPAIR_TIME)

        self.process = env.process(self.working(repairman))
        env.process(self.break_machine())

    def working(self, repairman):

        while True:
            done_in = time_per_part()
            while done_in:
                try:
                    start = self.env.now
                    yield self.env.timeout(done_in)
                    done_in = 0

                except simpy.Interrupt:
                    self.broken = True
                    done_in -= self.env.now - start

                    with repairman.request(priority=1) as req:
                        yield req
                        yield self.env.timeout(REPAIR_TIME)

                    self.broken = False

            self.parts_made += 1

    def break_machine(self):
        while True:
            yield self.env.timeout(time_to_failure())
            if not self.broken:
                self.process.interrupt()

    def loss_calculation(self):
        if LOSS * REPAIR_TIME > WAGE * REPAIR_TIME:
            self.repairman += 1
        else:
            self.repairman = self.repairman
           

def other_jobs(env, repairman):
    while True:
        done_in = AT_MEAN
        while done_in:

            with repairman.request(priority=2) as req:
                yield req
                try:
                    start = env.now
                    yield env.timeout(done_in)
                    done_in = 0
                except simpy.Interrupt:
                    done_in -= env.now - start

print('Machine shop')
random.seed(RANDOM_SEED)

env = simpy.Environment()
repairman = simpy.PreemptiveResource(env, capacity=TECH_NO_INI)
machines = [Machine(env, 'Machine %d' % i, repairman, AT_MEAN, REPAIR_TIME)
            for i in range(NUM_MACHINES)]
env.process(other_jobs(env, repairman))

env.run(until=SIM_TIME)

print('Optimal number of technicians :', repairman)

