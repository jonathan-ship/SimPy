import random
import simpy


RANDOM_SEED = 42
PT_MEAN = 18.0 / 60    # EA / min
MTTF = 0.01 / 60       # BREAKS / min
REPAIR_TIME = 120      # Time it takes to repair a machine in minutes (exp.)
JOB_DURATION = 9999    # Duration of other jobs in minutes
NUM_MACHINES = 10      # Number of machines in the machine shop
SIM_TIME = 10000  # Simulation time in minutes

BREAK_COST = 100000 # per hour
TECHINICIAN_COST = 30000 # per hour



def time_per_part():
    """Return actual processing time for a concrete part."""
    return random.expovariate(PT_MEAN)


def time_to_failure():
    """Return time until next failure for a machine."""
    return random.expovariate(MTTF)

def time_to_repair():
    """Return time until next failure for a machine."""
    return random.expovariate(1 / REPAIR_TIME)


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
        self.TOTAL_BREAK_COST = 0

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
                    start_stop_time = self.env.now
                    done_in -= self.env.now - start  # How much time left?

                    # Request a repairman. This will preempt its "other_job".
                    with repairman.request(priority=1) as req:
                        yield req
                        # print(self.name + "repairman start: ", self.env.now)
                        REPAIR_TIME = time_to_repair()
                        yield self.env.timeout(REPAIR_TIME)
                        # print("repairman is done: ", self.env.now)

                    self.broken = False
                    end_stop_time = self.env.now
                    self.TOTAL_BREAK_COST += BREAK_COST * (end_stop_time - start_stop_time) / 60

            # Part is done.
            self.parts_made += 1

    def break_machine(self):
        """Break the machine every now and then."""
        while True:
            failure_time = time_to_failure()
            yield self.env.timeout(failure_time)
            # self.TOTAL_BREAK_COST += BREAK_COST * failure_time / 60
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

# Create an environment and start the setup process
for i in range(20):
    random.seed(RANDOM_SEED)  # This helps reproducing the results
    env = simpy.Environment()
    repairman = simpy.PreemptiveResource(env, capacity=i+1)
    machines = [Machine(env, 'Machine %d' % j, repairman)
                for j in range(NUM_MACHINES)]
    env.process(other_jobs(env, repairman))

    technician_cost = TECHINICIAN_COST * (i+1) * SIM_TIME / 60.0


    # Execute!
    env.run(until=SIM_TIME)

    TOTAL_BREAK_COST = 0
    for j in range(NUM_MACHINES):
        TOTAL_BREAK_COST += machines[j].TOTAL_BREAK_COST
        # print('Machine %d made %d parts.' % (j, machines[j].parts_made))

    print('Total cost: ', TOTAL_BREAK_COST + technician_cost)
    print('Total break cost: ', TOTAL_BREAK_COST)
    print('Total technician cost: ', technician_cost)

"""
결론적으로, 현재의 고장 빈도 상 수리기사가 1명일 때는 모든 고장을 바로 고치지 못하지만,
2명 이상부터는 break cost가 동일한 것으로 보아 모든 고장을 바로 고칠 수 있음을 알 수 있다.
다만, technician cost가 고장이 발생하는 빈도에 비해 지나치게 높고, 낭비되는 시간이 많아
technician cost의 증가(500만 KRW)가 break cost의 감소(약 100만KRW)보다 더 크게 나타난다.
따라서 최적의 수리기사 수는 1명이다.
"""
