import simpy

class Fuel_station():
    def __init__(self, env, charging_duration, IAT, station):
        self.env = env
        self.charging = charging_duration
        self.IAT = IAT
        self.station = station

        self.action = env.process(self.run())

    def run(self):
        car_index = 0
        for _ in range(4):
            car_index += 1
            self.env.process(self.car(car_index))
            yield self.env.timeout(self.IAT)

    def car(self, car_index):
        print('{0} arriving at'.format(car_index), self.env.now)
        yield self.station.put(car_index)
        print('{0} starting to charge at'.format(car_index), self.env.now)
        print('In the station :', self.station.items)
        yield self.env.timeout(self.charging)
        out = yield self.station.get()
        print('{0} leaving the station at'.format(out), self.env.now)


env = simpy.Environment()
station = simpy.Store(env, capacity=2)
charging_duration =5
IAT = 2

fuel_station = Fuel_station(env, charging_duration, IAT, station)
env.run()