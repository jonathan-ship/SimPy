"""
Jiwon Baek
Topics in Ship Production Engineering Final Exam
Problem 1-Numerical Soulution
"""


import simpy
import numpy as np
import math
import pandas as pd
import matplotlib.pyplot as plt

RANDOM_SEED = 42


WEEKS = 4              # Simulation time in weeks
SIM_TIME = WEEKS * 7 * 24 * 60  # Simulation time in minutes

class Part:
    def __init__(self, id, enter_time):
        self.id = id
        self.enter_time = enter_time
        self.started_time = 0
        self.finished_time = 0


class Source:
    def __init__(self, env, model, name, mean_IAT):
        self.env = env
        self.model = model
        self.mean_IAT = mean_IAT
        self.name = name
        self.part_id = 0
        self.env.process(self.processing())
        self.create_log = []

    def processing(self):
        while True:
            self.part_id += 1
            part = Part(self.part_id, enter_time=self.env.now)
            self.create_log.append(self.env.now)
            self.model['M1'].store.put(part)
            IAT = np.random.exponential(self.mean_IAT)
            yield self.env.timeout(IAT)


class Sink:
    def __init__(self, env, model, name):
        self.env = env
        self.model = model
        self.name = name
        self.store = simpy.Store(env)
        self.env.process(self.processing())

        self.part_count = 0

    def processing(self):
        while True:
            part = yield self.store.get()
            self.part_count += 1


class Process:
    def __init__(self, env, repairman, t0, c02, mtbf, mttr, model, name, next_process_name):
        self.model = model
        self.name = name
        self.next_process_name = next_process_name
        self.total_working_time = 0.0
        self.service_time = 0.0
        self.parts_made = 0
        self.broken = False
        self.env = env
        self.availability = self.env.event()
        self.t0 = t0
        self.c02 = c02
        self.std_t0 = math.sqrt(self.c02 * math.pow(self.t0, 2))
        self.mtbf = mtbf
        self.mttr = mttr
        self.machines = simpy.Resource(env, capacity=1)
        self.env = env
        self.store = simpy.Store(env)
        self.log_start = []
        self.log_finish = []
        self.process = env.process(self.processing(repairman))
        self.start=0
        env.process(self.break_machine())

    def processing(self, repairman):
        while True:
            req = self.machines.request()
            yield req
            part = yield self.store.get()
            self.availability.succeed()
            self.log_start.append(self.env.now)

            """
            Normal -> Exponential
            """
            done_in = np.random.exponential(self.t0)
            self.service_time = done_in
            print(self.name, 'started processing part %d at %4.2f' % (part.id, self.env.now))
            part.started_time = self.env.now

            while done_in:
                try:
                    # Working on the part
                    self.start = self.env.now
                    yield self.env.timeout(done_in)
                    done_in = 0  # Set to 0 to exit while loop.

                except simpy.Interrupt:
                    print(self.name, '- Machine Breakdown occurred in %4.2f' %self.env.now)
                    self.broken = True
                    done_in -= self.env.now - self.start  # How much time left?

                    # Request a repairman. This will preempt its "other_job".
                    with repairman.request(priority=1) as req:
                        yield req
                        yield self.env.timeout(np.random.exponential(self.mttr))

                    print(self.name, '- Machine Repaired in %4.2f' % self.env.now)
                    self.broken = False

            print(self.name, 'finished processing part %d at %4.2f' % (part.id, self.env.now))
            part.finished_time = self.env.now
            self.log_finish.append(self.env.now)
            self.env.process(self.to_next_process(part, req, self.next_process_name))
            self.total_working_time += self.service_time

            self.availability = self.env.event()

    def break_machine(self):
        """Break the machine every now and then."""
        while True:
            yield self.env.timeout(self.mtbf)
            if (not self.broken):
                yield self.availability
                # Only break the machine if it is currently working.
                self.process.interrupt()

    def to_next_process(self, part, req, next_process_name):
        yield self.model[next_process_name].store.put(part)
        self.machines.release(req)

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

np.random.seed(5)

env = simpy.Environment()
repairman1 = simpy.PreemptiveResource(env, capacity=1)
repairman2 = simpy.PreemptiveResource(env, capacity=1)

model = {}
# env, repairman, t0, c02, mtbf, mttr, model, name, next_process_name
model['source'] = Source(env, model, 'source', 10)
model['M1'] = Process(env, repairman1, 19, 0.25, 48*60, 8*60, model, 'M1', 'M2')
model['M2'] = Process(env, repairman2, 22, 1.0, 3.3*60, 10, model, 'M2', 'sink')
model['sink'] = Sink(env, model, 'sink')
env.process(other_jobs(env, repairman1))
env.process(other_jobs(env, repairman2))

env.run(until=SIM_TIME)


"""
Output Example

M1 started processing part 149 at 2876.45
M1 - Machine Breakdown occurred in 2880.00
M1 - Machine Repaired in 3077.02
M1 finished processing part 149 at 3121.95
"""