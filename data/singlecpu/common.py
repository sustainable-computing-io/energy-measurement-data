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
    features = [f for f in node_stat.columns if 'curr' in f and 'cpu_' in f]
    node_stat = node_stat[features].reset_index()
    node_stat.columns = node_stat.columns.str.replace('curr_', '')
    return node_stat

def get_target_stat(query_data, target='coremark'):
    pod_energy_stat = query_data['kepler_pod_energy_stat']
    target_stat = pod_energy_stat[pod_energy_stat['container_name']==target]
    features = [f for f in target_stat.columns if 'curr_' in f and 'cpu_' in f]
    target_stat = target_stat.groupby(['time']).sum()[features].reset_index()
    target_stat.columns = target_stat.columns.str.replace('curr_', '')
    return target_stat




