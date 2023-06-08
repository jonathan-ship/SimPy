import simpy
import random
import numpy as np

RANDOM_SEED = 42
c=10
arrival_rate=18
arrival_time=1/arrival_rate
service_time=1/3
service_rate=1/service_time
MTBF=1/0.01
repair_time=2
breakdown_cost=100000
repair_man=1
repair_man_payment=30000
SIM_TIME=10000

class Repair(object):
    def __init__(self, env, service_rate, repair_man, arrival_time, repair_time, MTBF):
        self.env = env
        self.service_rate = service_rate
        self.arrival_time = arrival_time
        self.broken = False

        # record time each customer spends in system
        self.time_repair=[]

        # Start "working"
        self.process = env.process(self.source(arrival_time, repair_man, service_rate))
        env.process(self.break_machine())

    def source(self, arrival_time, resource, service_rate):
        i = 0
        while True:
            done_in=random.expovariate(service_rate)
            while done_in:
                try:
                    #working on the part
                    start=env.now
                    c = self.customer('Customer%02d' % i, resource, service_rate)
                    env.process(c)
                    t = random.expovariate(1.0 / arrival_time)
                    yield env.timeout(t)
                    i += 1
                    done_in=0
                except simpy.Interrupt:
                    print("broken")
                    broken=env.now
                    self.broken=True
                    done_in -= self.env.now - start
                    # print('%7.4f %s: Broken' % (env.now))
                    
                    with resource.request(priority=1) as req:
                        yield req
                        yield self.env.timeout(random.expovariate(1/repair_time))
                    fixed=env.now
                    self.broken=False
                    self.time_repair.append(fixed-broken)
                    print("fixed")

    def break_machine(self):
        while True:
            yield self.env.timeout(random.expovariate(MTBF))
            if not self.broken:
                self.process.interrupt()

    def customer(self, name, resource, service_time):
        arrive = env.now
        print('%7.4f %s: Here I am' % (arrive, name))
        with resource.request() as req:
            yield req
            start = env.now
            wait = env.now - arrive

            # We got to the repair shop
            print('%7.4f %s: Waited %6.3f' % (env.now, name, wait))

            # repairing
            yield env.timeout(service_time)
            print('%7.4f %s: Finished' % (env.now, name))
            finish = env.now

env=simpy.Environment()
repairman=simpy.PreemptiveResource(env, capacity=c)
repair=Repair(env, service_rate, repairman, arrival_time, repair_time, MTBF)
env.run(until=SIM_TIME)

broken_time=np.sum(repair.time_repair)
print(broken_time)
