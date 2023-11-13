import random

import simpy

RANDOM_SEED = 42

NUM_MACHINES = 10

Lambda = 18
Mu = 3 

BREAK_MEAN = 0.01
REPAIR_MEAN = 1 / 2

SIM_TIME = 10000

Loss = 100000
Wage = 30000

class Factory:
    def __init__(self, env, num_machines):
        self.env = env
        self.machine = simpy.Resource(env, num_machines)

    def process(self):
        yield self.env.timeout(random.expovariate(Mu))

class Machine(object):
    def __init__(self, env, name, repairman):
        self.env = env
        self.name = name
        self.parts_made = 0
        self.broken = False

        self.repair_time_list = []

        # Start "working" and "break_machine" processes for this machine.
        self.process = env.process(self.working(repairman))
        env.process(self.break_machine())

    def working(self, repairman):
        while True:
            # Start making a new part
            done_in = random.expovariate(Mu)
            while done_in:
                try:
                    # Working on the part
                    start = self.env.now
                    yield self.env.timeout(done_in)
                    done_in = 0  # Set to 0 to exit while loop.

                except simpy.Interrupt:
                    self.broken = True
                    done_in -= self.env.now - start  # How much time left?

                    # Request a repairman. This will preempt its "other_job".
                    with repairman.request(priority=1) as req:
                        repair_time = random.expovariate(REPAIR_MEAN)
                        self.repair_time_list.append(repair_time)
                        yield req
                        yield self.env.timeout(repair_time)

                    self.broken = False

            # Part is done.
            self.parts_made += 1

    def break_machine(self):
        """Break the machine every now and then."""
        while True:
            yield self.env.timeout(random.expovariate(BREAK_MEAN))
            if not self.broken:
                # Only break the machine if it is currently working.
                self.process.interrupt()


def other_jobs(env, repairman):
    """The repairman's other (unimportant) job."""
    while True:
        # Start a new job
        done_in = 30
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

# def steel(env, m):
#     print('%s arrives at the carwash at %.2f.' % (name, env.now))
#     with m.machine.request() as request:
#         yield request

#         print('%s enters the carwash at %.2f.' % (name, env.now))
#         yield env.process(m.wash(name))

#         print('%s leaves the carwash at %.2f.' % (name, env.now))


# def setup(env, num_machines, washtime, t_inter):
#     machine = Machine(env, num_machines, washtime)

#     while True:
#         yield env.timeout(random.expovariate(Lambda))
#         env.process(steel(env, machine))


# Setup and start the simulation
print('Machine shop')
random.seed(RANDOM_SEED)  # This helps reproducing the results

# Create an environment and start the setup process
env = simpy.Environment()
# env.process(setup(env, ))
repairman = simpy.PreemptiveResource(env, capacity=1)
machines = [Machine(env, 'Machine %d' % i, repairman)
            for i in range(NUM_MACHINES)]
env.process(other_jobs(env, repairman))

# Execute!
env.run(until=SIM_TIME)

# Analyis/results
# print('Machine shop results after %s weeks' % WEEKS)
for machine in machines:
    print(machine.name, machine.repair_time_list)