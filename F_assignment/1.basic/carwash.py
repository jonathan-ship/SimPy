"""
Carwash example.

Covers:

- Waiting for other processes
- Resources: Resource

Scenario:
  A carwash has a limited number of washing machines and defines
  a washing processes that takes some (random) time.

  Car processes arrive at the carwash at a random time. If one washing
  machine is available, they start the washing process and wait for it
  to finish. If not, they wait until they an use one.

"""
import random
import simpy
import numpy as np
import matplotlib.pyplot as plt

from mpl_toolkits.mplot3d import Axes3D


RANDOM_SEED = 42
NUM_MACHINES = 2  # Number of machines in the carwash
WASHTIME = 5      # Minutes it takes to clean a car
T_INTER = 7       # Create a car every ~7 minutes
MONITORING_INTER = 1 # monitoring time interval
SIM_TIME = 1000     # Simulation time in minutes


class Monitor(object):
    def __init__(self, env, num_machines, monitoring_inter):
        self.env = env
        self.num_machines = num_machines
        self.monitoring_inter = monitoring_inter
        self.working_time = 0.0
        self.time = []
        self.utilization = []
        self.process = env.process(self.run())

    def run(self):
        while True:
            yield self.env.timeout(self.monitoring_inter)
            u = self.working_time / (self.env.now * self.num_machines)
            self.time.append(self.env.now)
            self.utilization.append(u)

    def graph_utilization(self):
        fig, ax = plt.subplots()
        ax.plot(self.time, self.utilization)
        ax.set_title("utilization of carwash")
        ax.set_xlabel("simulation_time")
        ax.set_ylabel("utilization")
        ax.set_ylim([0.0, 1.1])
        plt.show()


class Carwash(object):
    """A carwash has a limited number of machines (``NUM_MACHINES``) to
    clean cars in parallel.

    Cars have to request one of the machines. When they got one, they
    can start the washing processes and wait for it to finish (which
    takes ``washtime`` minutes).

    """
    def __init__(self, env, num_machines, washtime, monitor):
        self.env = env
        self.machine = simpy.Resource(env, num_machines)
        self.washtime = washtime
        self.monitor = monitor

    def wash(self, car):
        """The washing processes. It takes a ``car`` processes and tries
        to clean it."""
        yield self.env.timeout(self.washtime)
        self.monitor.working_time += self.washtime
        print("Carwash removed %d%% of %s's dirt." %
              (random.randint(50, 99), car))


def car(env, name, cw):
    """The car process (each car has a ``name``) arrives at the carwash
    (``cw``) and requests a cleaning machine.

    It then starts the washing process, waits for it to finish and
    leaves to never come back ...

    """
    print('%s arrives at the carwash at %.2f.' % (name, env.now))
    with cw.machine.request() as request:
        yield request

        print('%s enters the carwash at %.2f.' % (name, env.now))
        yield env.process(cw.wash(name))

        print('%s leaves the carwash at %.2f.' % (name, env.now))


def setup(env, num_machines, washtime, monitor, t_inter):
    """Create a carwash, a number of initial cars and keep creating cars
    approx. every ``t_inter`` minutes."""
    # Create the carwash
    carwash = Carwash(env, num_machines, washtime, monitor)

    # Create 4 initial cars
    for i in range(4):
        env.process(car(env, 'Car %d' % i, carwash))

    # Create more cars while the simulation is running
    while True:
        yield env.timeout(random.randint(t_inter - 2, t_inter + 2))
        i += 1
        env.process(car(env, 'Car %d' % i, carwash))


def optimize(washtime, t_inter, monitoring_inter, display=False):
    num_machines_optimized = 0
    average_u_optimized = 0.0
    deviation_of_u_optimized = float('inf')
    num_machines = []
    average_u = []
    deviation_of_u = []
    i = 1
    while True:
        env = simpy.Environment()
        monitor = Monitor(env, i, monitoring_inter)
        env.process(setup(env, i, washtime, monitor, t_inter))
        env.run(until=500)
        num_machines.append(i)
        average_u.append(monitor.utilization[-1])
        deviation_of_u.append(np.std(monitor.utilization))
        if average_u[-1] >= average_u_optimized + 0.01:
            average_u_optimized = average_u[-1]
            deviation_of_u_optimized = deviation_of_u[-1]
            num_machines_optimized = i
        elif (average_u[-1] < average_u_optimized + 0.01) and (average_u[-1] >= average_u_optimized - 0.01):
            if deviation_of_u[-1] < deviation_of_u_optimized:
                deviation_of_u_optimized = deviation_of_u[-1]
                num_machines_optimized = i
        else:
            if i >= 10:
                break
        i += 1

    if display:
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        line1 = ax1.plot(num_machines, average_u, label="average utilization", c="tab:blue")
        line2 = ax2.plot(num_machines, deviation_of_u, label="deviation of utilization", c="tab:orange")
        ax1.set_xlabel("number of machine")
        ax1.set_ylabel("average utilization")
        ax2.set_ylabel("deviation of utilization")
        ax1.set_ylim([0.0, 1.1])
        ax2.set_ylim([0.0, 0.5])
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels)
        plt.show()

    print(average_u)
    print(num_machines_optimized)

    return num_machines_optimized


def parameter_analysis(wash_time, t_inter):
    num_machines_optimized = np.full([len(t_inter), len(wash_time)], 0)

    for i in range(len(wash_time)):
        for j in range(len(t_inter)):
            num_machines_optimized[j, i] = optimize(wash_time[i], t_inter[j], MONITORING_INTER)

    n_max = np.max(num_machines_optimized)
    n_min = np.min(num_machines_optimized)
    N = n_max - n_min + 1
    x = list(wash_time - 0.5)
    x.append(x[-1] + 1.0)
    y = list(t_inter - 0.5)
    y.append(y[-1] + 1.0)
    fig, ax = plt.subplots()
    contour = ax.pcolormesh(x, y, num_machines_optimized, cmap=discrete_cmap(N, 'cubehelix'))
    contour.set_clim(n_min - 0.5, n_max + 0.5)
    ax.set_title("number of machines optimized")
    ax.set_xlabel("wash_time")
    ax.set_ylabel("t_inter")
    fig.colorbar(contour, ticks=range(n_min, n_max + 1))
    plt.show()


def discrete_cmap(N, base_cmap=None):
    """Create an N-bin discrete colormap from the specified input map"""

    # Note that if base_cmap is a string or None, you can simply do
    #    return plt.cm.get_cmap(base_cmap, N)
    # The following works for string, None, or a colormap instance:

    base = plt.cm.get_cmap(base_cmap)
    color_list = base(np.linspace(0, 1, N))
    cmap_name = base.name + str(N)
    return base.from_list(cmap_name, color_list, N)


if __name__ == "__main__":
    random.seed(RANDOM_SEED)

    # Example 1
    # Example of calculating the utilization
    env = simpy.Environment()
    monitor = Monitor(env, NUM_MACHINES, MONITORING_INTER)
    env.process(setup(env, NUM_MACHINES, WASHTIME, monitor, T_INTER))

    env.run(until=SIM_TIME)

    monitor.graph_utilization()

    # Example 2
    # Example of optimizing the number of machines to maximize utilization
    optimize(WASHTIME, T_INTER, MONITORING_INTER, display=True)

    # Example 3
    # Example of studying the relationship between the number of machine optimized and t_inter, wash_time
    wash_time = np.arange(15, 26)
    t_inter = np.arange(2, 11)
    parameter_analysis(wash_time, t_inter)