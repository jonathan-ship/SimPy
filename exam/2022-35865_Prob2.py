"""
Machine shop example

Covers:

- Interrupts
- Resources: PreemptiveResource

Scenario:
  A workshop has *n* identical machines. A stream of jobs (enough to
  keep the machines busy) arrives. Each machine breaks down
  periodically. Repairs are carried out by one repairman. The repairman
  has other, less important tasks to perform, too. Broken machines
  preempt theses tasks. The repairman continues them when he is done
  with the machine repair. The workshop works continuously.

"""
import random
import numpy as np

import simpy


RANDOM_SEED = 42
PT_MEAN = 20.0         # Avg. processing time in minutes
PT_SIGMA = 0.25         # Sigma of processing time
MTTF = 6000.0           # Mean time to failure in minutes
BREAK_MEAN = 1 / MTTF  # Param. for expovariate distribution
REPAIR_TIME = random.expovariate(1.0 / 120)   # Time it takes to repair a machine in minutes
#JOB_DURATION = 10.0    # Duration of other jobs in minutes
NUM_MACHINES = 10      # Number of machines in the machine shop
WEEKS = 4              # Simulation time in weeks
SIM_TIME = WEEKS * 7 * 24 * 60  # Simulation time in minutes


def time_per_part():
    """Return actual processing time for a concrete part."""
    return random.normalvariate(PT_MEAN, PT_SIGMA)


def time_to_failure():
    """Return time until next failure for a machine."""
    return random.expovariate(BREAK_MEAN)


class Machine(object):
    """A machine produces parts and my get broken every now and then.

    If it breaks, it requests a *repairman* and continues the production
    after the it is repaired.

    A machine has a *name* and a numberof *parts_made* thus far.

    """
    def __init__(self, env, name, repairman):
        self.env = env
        self.name = name
        self.parts_made = 0
        self.broken = False

        # Start "working" and "break_machine" processes for this machine.
        self.process = env.process(self.working(repairman))
        env.process(self.break_machine())

    def working(self, repairman):
        """Produce parts as long as the simulation runs.

        While making a part, the machine may break multiple times.
        Request a repairman when this happens.

        """
        while True:
            # Start making a new part
            done_in = time_per_part()
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
                        yield req
                        yield self.env.timeout(REPAIR_TIME)

                    self.broken = False

            # Part is done.
            self.parts_made += 1

    def break_machine(self):
        """Break the machine every now and then."""
        while True:
            yield self.env.timeout(time_to_failure())
            if not self.broken:
                # Only break the machine if it is currently working.
                self.process.interrupt()


def other_jobs(env, repairman):
    """The repairman's other (unimportant) job."""
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

def optimize(num_of_machine, service_time):
    num_of_machine = 0
    num_of_machine_optimized = 0
    service_time = 0
    simulation_time=0
    num_of_machine = [1, 2]
    service_time = [1, 2]
    for i in num_of_machine:
        for j in service_time:
            env = simpy.Environment()
            repairman = simpy.PreemptiveResource(env, capacity=i)
            #env.process(working(repairman))
            env.run()
            #if abs(env.now - 200) < abs(simulation_time - 200):
            #    simulation_time = env.now
            #    num_of_machine_optimized = i
            #    service_time_optimized = j
    return num_of_machine_optimized, simulation_time

# Setup and start the simulation
print('Machine shop')
random.seed(RANDOM_SEED)  # This helps reproducing the results

# Create an environment and start the setup process
env = simpy.Environment()
repairman = simpy.PreemptiveResource(env, capacity=1)
machines = [Machine(env, 'Machine %d' % i, repairman)
            for i in range(NUM_MACHINES)]
#env.process(other_jobs(env, repairman))
num_of_machine=np.arange(1,6)
service_time = np.arange(21,30)
#env.process(optimize(num_of_machine,service_time))


#num_of_machine_optimized, simulation_time \
#    = optimize(num_of_machine, service_time)

# Execute!
env.run(until=SIM_TIME)

# Analyis/results
print('Machine shop results after %s weeks' % WEEKS)
for machine in machines:
    print('%s made %d parts.' % (machine.name, machine.parts_made))

#    print("the number of machine opimized: {0}, service_time_optimized: {1} | simulation time: {2}"
#          .format(num_of_machine_optimized, service_time_optimized, simulation_time))