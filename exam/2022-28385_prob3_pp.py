import numpy as np
import pandas as pd

def get_CT(filepath):
    raw_data = pd.read_csv(filepath, index_col=0)
    part_data = raw_data['Part'].unique()
    created_data = raw_data[raw_data['Event'] == 'part created'].reset_index(drop=True)
    finish_data = raw_data[raw_data['Event'] == 'part finish'].reset_index(drop=True)

    CT_list = []


    for part in part_data:
        part_created = created_data[created_data['Part'] == part]
        part_finish = finish_data[finish_data['Part'] == part]
        start = part_created['Time'].to_list()
        finish = part_finish['Time'].to_list()
        if finish:
            CT_list.append(finish[0]-start[0])

    CT_avg = sum(CT_list) / len(CT_list)
    print(CT_avg)

if __name__ == '__main__':
    filepath = 'eventlog.csv'
    get_CT(filepath)
