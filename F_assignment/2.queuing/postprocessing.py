import numpy as np
import pandas as pd


class Monitor():
    def __init__(self):
        self.id = []
        self.time = []
        self.event = []

    def record(self, id, time, event):
        self.id.append(id)
        self.time.append(time)
        self.event.append(event)

    def save_file(self, file_name):
        log = pd.DataFrame({"ID": self.id, "Time": self.time, "Event": self.event})
        log.to_csv(file_name, index=False)

    def calculate_L(self):
        log = pd.DataFrame({"ID": self.id, "Time": self.time, "Event": self.event})
        duration = log["Time"].max()
        queue_entered = log[["ID", "Time"]][log["Event"] == "queue_entered"]
        service_finished = log[["ID", "Time"]][log["Event"] == "service_finished"]
        data = pd.merge(queue_entered, service_finished, left_on="ID", right_on="ID",
                        suffixes=("_queue_entered", "_service_finished"))
        data = data.dropna()
        L = np.sum(data["Time_service_finished"] - data["Time_queue_entered"]) / duration
        return L

    def calculate_L_Q(self):
        log = pd.DataFrame({"ID": self.id, "Time": self.time, "Event": self.event})
        duration = log["Time"].max()
        queue_entered = log[["ID", "Time"]][log["Event"] == "queue_entered"]
        service_finished = log[["ID", "Time"]][log["Event"] == "queue_released"]
        data = pd.merge(queue_entered, service_finished, left_on="ID", right_on="ID",
                        suffixes=("_queue_entered", "_queue_released"))
        data = data.dropna()
        L_Q = np.sum(data["Time_queue_released"] - data["Time_queue_entered"]) / duration
        return L_Q

    def calculate_W(self):
        log = pd.DataFrame({"ID": self.id, "Time": self.time, "Event": self.event})
        queue_entered = log[["ID", "Time"]][log["Event"] == "queue_entered"]
        service_finished = log[["ID", "Time"]][log["Event"] == "service_finished"]
        data = pd.merge(queue_entered, service_finished, left_on="ID", right_on="ID",
                        suffixes=("_queue_entered", "_service_finished"))
        data = data.dropna()
        W = np.mean(data["Time_service_finished"] - data["Time_queue_entered"])
        return W

    def calculate_W_Q(self):
        log = pd.DataFrame({"ID": self.id, "Time": self.time, "Event": self.event})
        queue_entered = log[["ID", "Time"]][log["Event"] == "queue_entered"]
        service_finished = log[["ID", "Time"]][log["Event"] == "queue_released"]
        data = pd.merge(queue_entered, service_finished, left_on="ID", right_on="ID",
                        suffixes=("_queue_entered", "_queue_released"))
        data = data.dropna()
        W_Q = np.mean(data["Time_queue_released"] - data["Time_queue_entered"])
        return W_Q