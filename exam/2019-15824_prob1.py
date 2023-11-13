"""
Jiwon Baek
Topics in Ship Production Engineering Final Exam
Problem 1 - Analytic Solution
"""

import numpy as np
import math
import matplotlib.pyplot as plt
import random
import simpy

RANDOM_SEED = 42
PT_MEAN = 10.0  # Avg. processing time in minutes
PT_SIGMA = 2.0  # Sigma of processing time
MTTF = 300.0  # Mean time to failure in minutes
BREAK_MEAN = 1 / MTTF  # Param. for expovariate distribution
REPAIR_TIME = 30.0  # Time it takes to repair a machine in minutes
JOB_DURATION = 30.0  # Duration of other jobs in minutes
NUM_MACHINES = 10  # Number of machines in the machine shop
WEEKS = 1  # Simulation time in weeks
SIM_TIME = WEEKS * 7 * 24 * 60  # Simulation time in minutes

"""
Analytical Solution
"""


class Workstation:
    def __init__(self, target_TH, t0, ca2, c02, mtbf, mttr):
        self.target_TH = target_TH
        self.t0 = t0
        self.ca2 = ca2
        self.c02 = c02
        self.mf = mtbf
        self.mr = mttr
        self.n_machine = 1

        self.te, self.ce2, self.cd2 = self.get_cd2(ca2, c02, mtbf, mttr, t0, target_TH)

        self.u = self.target_TH * self.te / 60

        if self.u < 1.0:
            self.calculate_VUT()

        else:
            # print('Invalid utilization, number of machine :', self.n_machine)
            self.u = 0.0
            self.V = 0.0
            self.U = 0.0

    def get_cd2(self, ca2, c02, mf, mr, t0, th):
        A = mf / (mf + mr)
        te = t0 / A
        """
        C_r is assumed as 1
        """
        ce2 = c02 + (1 + 1) * A * (1 - A) * mr / t0
        u2 = math.pow(th * te / 60, 2)
        cd2 = (1 - u2) * ca2 + u2 * ce2
        return te, ce2, cd2

    def calculate_VUT(self):
        self.U = self.u / (1 - self.u)
        self.V = (self.ca2 + self.ce2) / 2

    # # In case of revising the data manually while operating (for comparison)
    # def revise(self, new_CV):
    #     self.CVe_b = new_CV
    #     self.U = math.pow(self.u , math.sqrt(2*(self.n_machine+1))-1) / (self.n_machine * (1-self.u))
    #     self.V = (math.pow(self.CVa,2) + math.pow(self.CVe_b,2))/2

    def get_CVd(self):
        cvd = 1 + (1 - math.pow(self.u, 2)) * (self.ca2 - 1) + (
                math.pow(self.u, 2) / math.sqrt(self.n_machine)) * (self.ce2 - 1)

        # CVd can be negative in some occasions
        if cvd >= 0:
            cvd = math.sqrt(cvd)
        else:
            print('Error! CVd is negative')
            cvd = int(0)
        return cvd

    def get_CT(self):  # Calculate CT according to VUT formula
        ct = self.V * self.U * self.te + self.te
        return ct

    def get_CTq(self):  # Calculate CTq according to VUT formula
        ctq = self.V * self.U * self.te
        return ctq

    def get_WIP(self):  # Calculate WIP = TH x CT
        wip = self.target_TH * self.get_CT() / 60
        return wip

    def get_WIPq(self):  # Calculate WIPq = TH x CTq
        wipq = self.target_TH * self.get_CTq() / 60
        return wipq

    def print_status(self):
        print("WIP : ", self.get_WIP())
        print("WIPq : ", self.get_WIPq())
        print("CT : ", self.get_CT())
        print("CTq : ", self.get_CTq())
        print("u : ", self.u)
        print("te : ", self.te)
        print("CVb^2 : ", self.ce2)
        print("CVa^2 : ", self.ca2)
        print("CVd^2 : ", self.get_CVd() ** 2)


# (target_TH, t0, ca2, c02, mtbf, mttr):
w1 = Workstation(2.4, 19, 1, 0.25, 48 * 60, 8 * 60)
w2 = Workstation(2.4, 22, w1.cd2, 1.0, 3.3 * 60, 10)

print('----------W1----------')
w1.print_status()
print('----------W2----------')
w2.print_status()

"""
Result

----------W1----------
WIP :  26.68102941176472
WIPq :  25.794362745098056
CT :  667.025735294118
CTq :  644.8590686274514
u :  0.8866666666666667
te :  22.166666666666668
CVb^2 :  6.436895810955963
CVa^2 :  1
CVd^2 :  5.274366666666668
----------W2----------
WIP :  36.643947642701505
WIPq :  35.719503198257065
CT :  916.0986910675377
CTq :  892.9875799564267
u :  0.9244444444444444
te :  23.11111111111111
CVb^2 :  1.0416050295857988
CVa^2 :  5.274366666666668
CVd^2 :  1.6570590228806592

"""