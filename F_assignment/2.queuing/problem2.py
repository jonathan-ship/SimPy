import os
import simpy

from scipy.stats import *
from postprocessing import Monitor


def setup(env, server, monitor, arrival_rate, service_rate):
    i = 0
    while True:
        IAT = expon.rvs(scale=1/arrival_rate)
        yield env.timeout(IAT)
        monitor.record(i, env.now, "queue_entered")
        env.process(model(i, env, server, monitor, service_rate))
        i += 1


def model(id, env, server, monitor, service_rate):
    with server.request() as req:
        yield req
        monitor.record(id, env.now, "queue_released")

        service_time = expon.rvs(scale=1/service_rate)
        monitor.record(id, env.now, "service_started")
        yield env.timeout(service_time)
        monitor.record(id, env.now, "service_finished")


if __name__ == "__main__":
    file_path = "./result/problem2"
    if not os.path.exists(file_path):
        os.makedirs(file_path)

    arrival_rates = [5, 6, 7.2, 8.64, 10]
    service_rate = 10

    for arrival_rate in arrival_rates:
        env = simpy.Environment()
        server = simpy.Resource(env, capacity=1)
        monitor = Monitor()
        env.process(setup(env, server, monitor, arrival_rate, service_rate))
        env.run(until=10000000)

        monitor.save_file(file_path + "/log_lambda {0}.csv".format(arrival_rate))
        L = monitor.calculate_L()
        W = monitor.calculate_W()
        print("arrival rate: {0}".format(arrival_rate) + "-" * 50)
        print("average number of customers in system(L): {0}".format(L))
        print("average time customer spends in system(W): {0}".format(W))