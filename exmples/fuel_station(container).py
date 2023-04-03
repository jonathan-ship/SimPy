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
        self.env.process(self.fuel_tank())
        for _ in range(4):
            car_index += 1
            self.env.process(self.car(car_index))
            yield self.env.timeout(self.IAT)

    def car(self, car_index):
        print('{0} arriving at'.format(car_index), self.env.now)
        yield self.station.get(40)

        print('{0} starting to charge at'.format(car_index), self.env.now)
        print('{0} fuel left at'.format(self.station.level), self.env.now)
        yield self.env.timeout(self.charging)
        print('{0} leaving the station at'.format(car_index), self.env.now)

    def fuel_tank(self):
        while True:
            fuel_need = self.station.capacity - self.station.level
            if fuel_need>0:
                self.station.put(fuel_need)
            yield self.env.timeout(4)


env = simpy.Environment()
station = simpy.Container(env, capacity=100)
charging_duration =5
IAT = 2

fuel_station = Fuel_station(env, charging_duration, IAT, station)
env.run(15)