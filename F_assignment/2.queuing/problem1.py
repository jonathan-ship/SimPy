import os
import simpy

from scipy.stats import *
from postprocessing import Monitor


def setup(env, server, monitor, arrival_rate, service_time_mean, service_time_std):
    i = 0
    while True:
        IAT = expon.rvs(scale=1 / arrival_rate)
        yield env.timeout(IAT)
        monitor.record(i, env.now, "queue_entered")
        env.process(model(i, env, server, monitor, service_time_mean, service_time_std))
        i += 1


def model(id, env, server, monitor, service_time_mean, service_time_std):
    with server.request() as req:
        yield req
        monitor.record(id, env.now, "queue_released")

        lower = service_time_mean - service_time_mean
        upper = service_time_mean + service_time_mean
        service_time = truncnorm.rvs((lower - service_time_mean) / service_time_std,
                                     (upper - service_time_mean) / service_time_std,
                                     loc=service_time_mean, scale=service_time_std)
        monitor.record(id, env.now, "service_started")
        yield env.timeout(service_time)
        monitor.record(id, env.now, "service_finished")


if __name__ == "__main__":
    file_path = "./result/problem1"
    if not os.path.exists(file_path):
        os.makedirs(file_path)

    arrival_rate = 0.025
    service_time_mean = 30
    service_time_std = 20

    env = simpy.Environment()
    server = simpy.Resource(env, capacity=1)
    monitor = Monitor()
    env.process(setup(env, server, monitor, arrival_rate, service_time_mean, service_time_std))
    env.run(until=10000000)

    monitor.save_file(file_path + "/log.csv")
    L = monitor.calculate_L()
    print("average number of customers in system(L): {0}".format(L))


