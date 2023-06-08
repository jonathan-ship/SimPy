import simpy
import numpy as np

NUM_MACHINES = 10
arrival_rate = 18  # per hour (poisson)
iat = 60 / arrival_rate  # minutes (exp)
t_0 = 20  # minutes (exp)

breakdown_rate = 0.01  # per hour (poisson)
ibt = 60 / breakdown_rate  # minutes (exp)

repair_time = 2 * 60  # minutes (exp)

breakdown_cost = 100000  # per hour

repairman_cost = 30000  # per hour

RANDOM_SEED = 42
WEEKS = 4
SIM_TIME = WEEKS * 7 * 24 * 60  # minutes

JOB_DURATION = 30  # minutes


def time_per_part():
    """Return actual processing time for a concrete part."""
    return np.random.exponential(t_0)


def time_to_failure():
    """Return time until next failure for a machine."""
    return np.random.exponential(ibt)


def time_to_repair():
    return np.random.exponential(repair_time)


class Machine(object):
    def __init__(self, env, name, repairman):
        self.env = env
        self.name = name
        self.parts_made = 0
        self.broken = False

        self.total_machine_breakdown_time = 0

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
                    time_broken = self.env.now
                    self.broken = True
                    done_in -= self.env.now - start  # How much time left?

                    # Request a repairman. This will preempt its "other_job".
                    with repairman.request(priority=1) as req:
                        yield req
                        yield self.env.timeout(time_to_repair())
                        time_fix_finished = self.env.now

                    breakdown_time = time_fix_finished - time_broken
                    self.total_machine_breakdown_time += breakdown_time

                    self.broken = False

            # Part is done.
            self.parts_made += 1

    def break_machine(self):
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


# Setup and start the simulation
print('Machine shop')

total_cost_list = []

for i in range(1, 20):
    num_repairman = i

    np.random.seed(RANDOM_SEED)  # This helps reproducing the results

    # Create an environment and start the setup process
    env = simpy.Environment()
    repairman = simpy.PreemptiveResource(env, capacity=num_repairman)
    machines = [Machine(env, 'Machine %d' % i, repairman)
                for i in range(NUM_MACHINES)]
    env.process(other_jobs(env, repairman))

    # Execute!
    env.run(until=SIM_TIME)

    # Calculate costs
    total_machine_breakdown_time = sum([machine.total_machine_breakdown_time for machine in machines])
    total_machine_breakdown_cost = total_machine_breakdown_time / 60 * breakdown_cost

    total_repairman_cost = num_repairman * repairman_cost * SIM_TIME / 60

    total_cost = total_machine_breakdown_cost + total_repairman_cost
    total_cost_list.append(total_cost)


# find the minimum cost
min_cost = min(total_cost_list)
min_cost_index = total_cost_list.index(min_cost)

print(total_cost_list)

print('The minimum cost is %d' % min_cost)
print('The number of repairman is %d' % (min_cost_index + 1))
