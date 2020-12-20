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
                                     loc=service_time_mean, scale=service_time_std)[0]
        monitor.record(id, env.now, "service_started")
        yield env.timeout(service_time)
        monitor.record(id, env.now, "service_finished")


if __name__ == "__main__":
    file_path = "./result/problem4"
    if not os.path.exists(file_path):
        os.makedirs(file_path)

    arrival_rate = 2
    service_time_mean = 1/1.5
    service_time_std = 0.5

    env = simpy.Environment()
    server = simpy.Resource(env, capacity=3)
    monitor = Monitor()
    env.process(setup(env, server, monitor, arrival_rate, service_time_mean, service_time_std))
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