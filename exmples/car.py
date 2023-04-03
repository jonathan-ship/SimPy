import simpy

class Car():
    def __init__(self, env, parking_duration, trip_duration):
        self.env = env
        self.parking = parking_duration
        self.driving = trip_duration
        self.action = env.process(self.run())

    def run(self):
        while True:
            print('Start driving at', self.env.now)
            yield self.env.timeout(self.driving)

            print('Start parking at', self.env.now)
            yield self.env.timeout(self.parking)


env = simpy.Environment()
parking_duration = 5
trip_duration = 2

car = Car(env, parking_duration, trip_duration)
env.run(until=15)