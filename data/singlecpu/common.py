import pandas as pd
import seaborn as sns

# read podstat (json)
import json
query_top_folder = "../query_output"
non_numerical = ["__name__", "instance", "node_name", "cpu_architecture", "command", "container", "endpoint", "instance", "job", "namespace", "pod", "pod_name", "pod_namespace", "service", "benchmark", "cluster", "t", "chip", "sensor", "exported_instance"]
min_timestamp = -1

pod_stat_query = 'kepler_pod_energy_stat'

def transform_elapse_time(timestamp):
    global min_timestamp
    return int(timestamp- min_timestamp)

def read_json(data_file):
    output = dict()
    with open(data_file, "r") as f:
        data = json.load(f)
    for query, response in data.items():
        items = []
        print(query)
        for res in response:
            metric_item = res["metric"]
            for val in res["values"]:
                item = metric_item.copy()
                item["timestamp"] = val[0]
                item["value"] = val[1] 
                items += [item]
        df = pd.DataFrame(items)
        
        for col in df.columns:
            if col in non_numerical:
                continue
            try:
                df[col] = df[col].astype(float)
            except:
               # print("cannot convert ",col)
                pass
        global min_timestamp
        if len(df) == 0:
            print("no data ", query)
            continue
        min_timestamp = min(df["timestamp"])
        df["time"] = df["timestamp"].transform(transform_elapse_time)
        df = df[df["service"]=="kepler-exporter"]
        output[query] = df
    return output

def get_node_stat(query_data):
    node_stat = query_data['kepler_pod_energy_stat'].groupby(['time']).sum()
    features = [f for f in node_stat.columns if 'curr' in f and ('cpu_' in f or 'cache_' in f)]
    node_stat = node_stat[features].reset_index()
    node_stat.columns = node_stat.columns.str.replace('curr_', '')
    return node_stat

def get_total_power(query_data):
    _node_power = query_data['kepler_node_platform_joules_total'].groupby(['time']).sum()['value'].reset_index()
    _node_power = _node_power[_node_power['value']>0]
    _node_power = _node_power[_node_power['value']<1000]
    return _node_power

def get_cpu_frequency(query_data):
    cpu_frequency = query_data['kepler_node_cpu_scaling_frequency_hertz']
    cpu_frequency['cpu'] = cpu_frequency['cpu'].astype(int)
    cpu_frequency['freq_hz'] = cpu_frequency['value']
    cpu_frequency = cpu_frequency[['time', 'cpu', 'freq_hz']].groupby(['time', 'cpu']).mean()
    return cpu_frequency

def get_package_power(query_data):
    package_energy = query_data['kepler_node_package_joules_total'].groupby(['time', 'package']).sum()
    _package_energy = package_energy.reset_index()
    package_power = None
    for package in pd.unique(_package_energy['package']):
        df = _package_energy[_package_energy['package'] == int(package)]
        df = df.sort_values(by=['time']).set_index(['time', 'package'])['value'].diff().dropna()
        df = df.mask(df.lt(0)).ffill().fillna(0).convert_dtypes()
        if package_power is None:
            package_power = df
        else:
            package_power = pd.concat([package_power, df])
    return package_power

import os
query_output_toppath = "./query_output"
level = "bm"
workload = "coremark_4threads_to_32threads_5rep_vm"

if __name__ == '__main__':
    query_output = os.path.join(query_output_toppath, level, workload + ".json")
    query_data = read_json(query_output)
    print(get_node_stat(query_data))
    print(get_cpu_frequency(query_data))
    print(get_total_power(query_data))
    print(get_package_power(query_data))