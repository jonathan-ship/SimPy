import random
import simpy

RANDOM_SEED = 42
PT_MEAN = 60/18         # Avg. processing time in minutes
PT_SIGMA = 20           # Sigma of processing time
MTTF = 60/0.01          # Mean time to failure in minutes
BREAK_MEAN = 1 / MTTF   # Param. for expovariate distribution
REPAIR_TIME = 120       # Time it takes to repair a machine in minutes
JOB_DURATION = 30.0     # Duration of other jobs in minutes
NUM_MACHINES = 10       # Number of machines in the machine shop
day = 1                 # Simulation time in weeks
idle = 24 * 18 * 60
SIM_TIME = 1 * 24 * 60  # Simulation time in minutes


def time_per_part():
    return random.expovariate(PT_SIGMA)


def time_to_failure():
    return random.expovariate(BREAK_MEAN)


class Machine(object):
    def __init__(self, env, name, repairman):
        self.env = env
        self.name = name
        self.parts_made = 0
        self.broken = False
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


def other_jobs(env, repairman):
    while True:
        # Start a new job
        done_in = JOB_DURATION
        while done_in:
            # Retry the job until it is done.
            # It's priority is lower than that of machine repairs.
            with repairman.request(priority=2) as req:
                yield req
                try:
                    start = env.now
                    yield env.timeout(done_in)
                    done_in = 0
                except simpy.Interrupt:
                    done_in -= env.now - start


# Setup and start the simulation
print('Prob_2')
random.seed(RANDOM_SEED)  # This helps reproducing the results

# Create an environment and start the setup process
env = simpy.Environment()
repairman = simpy.PreemptiveResource(env, capacity=1)
machines = [Machine(env, 'Machine %d' % i, repairman)
            for i in range(NUM_MACHINES)]
env.process(other_jobs(env, repairman))

# Execute!
env.run(until=SIM_TIME)

# Analyis/results
for machine in machines:
    print('%s made %d parts.' % (machine.name, machine.parts_made))

print('idle parts : %d' % (idle))
