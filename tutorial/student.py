import simpy
import numpy as np

## There is a library and there are only 2 seats → It creates a resource with a capacity of 2.
## Students arrive randomly, and if there is no seat at the time of arrival, wait as it is → Creates a student as a generator and passes it to the process.

def Student(env, num, library, arrive_time):
    ## Students arrive after 'arrive_time'
    yield env.timeout(arrive_time)
    print("student {} arrived library at {:6.2f}".format(num, env.now))
    waiting_time = env.now

    ## Following form (with/as) activate get and release automatically.
    ## In case of using in other forms, req = library.request(), library.release(req) should be used.
    with library.request() as req:
        yield req  ## wait until resource(here, library) is available
        waiting_time = env.now - waiting_time
        ## waiting_time =! 0 means that student has waited untl library seat is available
        if waiting_time != 0:
            print("student {} is waiting  during {:6.2f}".format(num, waiting_time))
        study_time = np.random.triangular(left=5, right=10, mode=8)
        print("student {} start to  study at {:6.2f}".format(num, env.now))
        if library.capacity == library.count:
            print("#### library full at  {:6.2f} ####".format(env.now))
        yield env.timeout(study_time)
        print("student {} end   to  study at {:6.2f}".format(num, env.now))
        print("#### library seat available at {:6.2f} ####".format(env.now))


env = simpy.Environment()
library = simpy.Resource(env, capacity=2)

for i in range(0, 5):
    arrive_time = np.random.triangular(left=1, right=8, mode=3)
    stu = Student(env, i, library, arrive_time)
    env.process(stu)

env.run(until=50)