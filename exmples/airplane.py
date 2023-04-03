import simpy

class Airplane():
    def __init__(self, env, trip_duration, charging_duration):
        self.env = env
        self.trip = trip_duration
        self.charging = charging_duration

        self.action = env.process(self.run())

    def run(self):
        airplane_index = 0
        while True:
            airplane_index += 1
            print('Airplane{0} starts trip at'.format(airplane_index), self.env.now)
            yield self.env.timeout(self.trip)
            print('Airplane{0} arrives in parking lot at'.format(airplane_index), self.env.now)

            print('Airplane{0} starts parking and charging at'.format(airplane_index), self.env.now)
            try:
                yield self.env.process(self.charge(airplane_index))
            except simpy.Interrupt:
                print("Interrupt at", self.env.now)

    def charge(self, airplane_index):
        yield self.env.timeout(self.charging)
        print('Airplane{0} finishes charging at'.format(airplane_index), self.env.now)

def interrupt(env, airplane):
    yield env.timeout(3)
    airplane.action.interrupt()


env = simpy.Environment()
trip_duration = 2
charging_duration = 5

airplane = Airplane(env, trip_duration, charging_duration)
env.process(interrupt(env, airplane))
env.run(until=15)