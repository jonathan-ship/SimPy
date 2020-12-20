import os
import simpy

from scipy.stats import *
from postprocessing import Monitor


def setup(env, calling_population, server, monitor, arrival_rate, service_rate):
    for i in range(calling_population):
        env.process(model(i, env, server, monitor, arrival_rate, service_rate))


def model(id, env, server, monitor, arrival_rate, service_rate):
    i = 0
    while True:
        IAT = expon.rvs(scale=1 / arrival_rate)
        yield env.timeout(IAT)
        monitor.record(str(id) + "_" + str(i), env.now, "queue_entered")

        with server.request() as req:
            yield req
            monitor.record(str(id) + "_" + str(i), env.now, "queue_released")

            service_time = expon.rvs(scale=1 / service_rate)
            monitor.record(str(id) + "_" + str(i), env.now, "service_started")
            yield env.timeout(service_time)
            monitor.record(str(id) + "_" + str(i), env.now, "service_finished")
        i += 1


if __name__ == "__main__":
    file_path = "./result/problem5"
    if not os.path.exists(file_path):
        os.makedirs(file_path)

    calling_population = 10
    arrival_rate = 0.05
    service_rate = 0.2

    env = simpy.Environment()
    server = simpy.Resource(env, capacity=2)
    monitor = Monitor()
    setup(env, calling_population, server, monitor, arrival_rate, service_rate)
    env.run(until=10000000)

    monitor.save_file(file_path + "/log.csv")
    L_Q = monitor.calculate_L_Q()
    L = monitor.calculate_L()
    W = monitor.calculate_W()
    W_Q = monitor.calculate_W_Q()
    print("average number of customers in queue(L_Q): {0}".format(L_Q))
    print("average number of customers in system(L): {0}".format(L))
    print("average time customer spends in system(W): {0}".format(W))
    print("average time customer spends in queue(W_Q): {0}".format(W_Q))