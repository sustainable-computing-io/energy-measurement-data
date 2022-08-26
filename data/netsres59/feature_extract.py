# input data description: 
#  - status_folder/pkg_map: mapping CPU core number to package ID
#  - query_top_folder/: prometheus query data in json format
#                - pod_energy_stat
#                - node_cpu_scaling_frequency_hertz
#                - node_package_energy_millijoule
#                - pod_cpu_cpu_time_us
# output data description:
# - common data: cpu_frequency.csv, package_power.csv, pod_cpu_stat.csv
# - extraction approach specific data: metadata, x, y, scaler, freq, freq_scaler

import pandas as pd
import numpy as np
import json
import os
import pickle

output_folder_key = "model_data_input"
pkg_map_file = "pkg_map.json"
query_top_folder = "./query_output"
status_folder = "./workload-status"

pod_stat_query = 'pod_energy_stat'
node_pkg_query = 'node_package_energy_millijoule'
freq_query = 'node_cpu_scaling_frequency_hertz'
pod_cpu_time_query = 'pod_cpu_cpu_time_us'

feature_extracting_methods = ['append', 'aggr']
non_numerical = ["__name__", "instance", "node_name", "cpu_architecture", "command", "container", "endpoint", "instance", "job", "namespace", "pod", "pod_name", "pod_namespace", "service", "benchmark", "cluster", "t", "chip", "sensor", "exported_instance"]

def transform_jobname(pod_name):
    return "-".join(pod_name.split("-")[0:3])

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
                print("cannot convert ",col)
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

def get_workload_path(workload):
    workload_spllits = workload.split('_')
    workload_prefix = '_'.join(workload_spllits[0:-1])
    output_folder = os.path.join(output_folder_key, workload_prefix)
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)
    output_folder = os.path.join(output_folder, workload_spllits[-1])
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)
    return output_folder

def new_output_folders(workload):
    output_folders = dict()
    if not os.path.exists(output_folder_key):
        os.mkdir(output_folder_key)
    for fe in feature_extracting_methods:
        output_folder = get_workload_path(workload)
        output_folders[fe] = output_folder + "/" + fe
        if not os.path.exists(output_folders[fe]):
            os.mkdir(output_folders[fe])
    return output_folders

def load_sample_data(workload):
    sample_data_file = query_top_folder + "/" + workload + ".json"
    sample_data = read_json(sample_data_file)
    return sample_data

def load_pkg_cpu():
    with open(status_folder + "/" + pkg_map_file, "r") as f:
        pkg_map_json = json.load(f)
        items = []
        for pkg, cpus in pkg_map_json.items():
            for cpu in cpus:
                item = {'pkg_id': int(pkg), 'cpu': int(cpu)}
                items += [item]
        pkg_map = pd.DataFrame(items)
        pkg_cpu = pkg_map.set_index('cpu')
        return pkg_cpu, pkg_map_json

def get_node_enery(sample_data):
    node_energy = sample_data[node_pkg_query]
    node_energy = node_energy[['timestamp', 'value']].set_index(['timestamp'])
    return node_energy

def get_package_energy(sample_data):
    package_energy = sample_data[node_pkg_query]
    package_energy['pkg_id'] = package_energy['pkg_id'].astype(int)
    package_energy['core'] = package_energy['value'] - package_energy['dram']
    package_energy['pkg'] = package_energy['value']
    package_energy = package_energy[['timestamp', 'pkg_id', 'core', 'dram', 'pkg']].set_index(['timestamp', 'pkg_id'])
    return package_energy

def get_package_power(sample_data, pkg_map_json):
    package_energy = get_package_energy(sample_data)
    _package_energy = package_energy.reset_index()

    package_power = None
    for pkg_id in pkg_map_json.keys():
        df = _package_energy[_package_energy['pkg_id'] == int(pkg_id)]
        df = df.sort_values(by=['timestamp']).set_index(['timestamp', 'pkg_id']).diff().dropna()
        df = df.mask(df.lt(0)).ffill().fillna(0).convert_dtypes()
        if package_power is None:
            package_power = df
        else:
            package_power = pd.concat([package_power, df])
    return package_power

def get_cpu_frequency(sample_data):
    cpu_frequency = sample_data[freq_query]
    cpu_frequency['cpu'] = cpu_frequency['cpu'].astype(int)
    cpu_frequency['freq_hz'] = cpu_frequency['value']
    cpu_frequency = cpu_frequency[['timestamp', 'cpu', 'freq_hz']].groupby(['timestamp', 'cpu']).mean()
    return cpu_frequency

def get_pod_cpu_stat(sample_data, pkg_cpu):
    pod_ts_index = ['pod_name', 'namespace', 'timestamp']
    # compute pod utilisation ratio on each cpu from pod_cpu_cpu_time_us dataset
    total_value = sample_data[pod_cpu_time_query].groupby(pod_ts_index).sum()['value']
    pod_ts_indexed_data = sample_data[pod_cpu_time_query].set_index(pod_ts_index + ['cpu'])
    pod_ts_indexed_data['ratio'] = pod_ts_indexed_data['value']/total_value
    pod_ts_indexed_data.reset_index(inplace=True)
    pod_ts_indexed_data['cpu'] = pod_ts_indexed_data['cpu'].astype(int)
    utilisation_ratio_per_cpu = pod_ts_indexed_data[pod_ts_index + ['cpu', 'ratio']]
    utilisation_ratio_per_cpu = utilisation_ratio_per_cpu.set_index(pod_ts_index + ['cpu'])
    # should be all 1
    # utilisation_ratio_per_cpu.groupby(pod_ts_index).sum()['ratio'].value_counts()

    # apply utilisation ratio to other stat in pod_energy_stat
    pod_stat = sample_data[pod_stat_query].set_index(pod_ts_index)
    print("columns:", pod_stat.columns)
    curr_metrics = [m for m in pod_stat.columns if ('curr' in m and 'energy' not in m and 'container' not in m) or 'process' in m]
    pod_stat = pod_stat[curr_metrics]

    df1 = utilisation_ratio_per_cpu.copy()
    # join ratio to stat metrics
    pod_cpu_stat = df1.join(pod_stat)
    # multiply by ratio
    pod_cpu_stat = pod_cpu_stat.multiply(utilisation_ratio_per_cpu["ratio"], axis="index").drop(columns=['ratio'])
    pod_cpu_stat = pod_cpu_stat.join(pkg_cpu)
    return pod_cpu_stat

def save_data(output_folders, fe, x_values, y_values, freq_values, metadata, scaler, freq_scaler):
    output_folder = output_folders[fe]
    metadata_file = output_folder + "/" + "metadata.json"
    x_file = output_folder + "/" + "x.npy"
    y_file = output_folder + "/" + "y.npy"
    freq_file = output_folder + "/" + "freq.npy"
    scaler_file = output_folder + "/" + "scaler.pkl"
    freq_scaler_file = output_folder + "/" + "freq_scaler.pkl"
    
    with open(metadata_file, "w") as f:
        json.dump(metadata, f)
    with open(x_file, "wb") as f:
        np.save(f, x_values)
    with open(y_file, "wb") as f:
        np.save(f, y_values)
    with open(freq_file, "wb") as f:
        np.save(f, freq_values)
    with open(scaler_file, "wb") as f:
        pickle.dump(scaler, f)
    with open(freq_scaler_file, "wb") as f:
        pickle.dump(freq_scaler, f)


from sklearn.preprocessing import MinMaxScaler

def get_job_stat(_pod_cpu_stat, metrics):
    # reduce the number of process to append by transform to jobname
    _pod_cpu_stat["job"] = _pod_cpu_stat["pod_name"].transform(transform_jobname)
    job_pkg_stat = _pod_cpu_stat.drop(columns=['pod_name', 'namespace', 'cpu']).groupby(['timestamp', 'pkg_id', 'job'])[metrics].sum()
    _job_pkg_stat = job_pkg_stat.reset_index().sort_values(['timestamp', 'pkg_id'])
    jobs = pd.unique(_job_pkg_stat['job'])
    jobs.sort()
    timestamps = pd.unique(_job_pkg_stat['timestamp'])
    return job_pkg_stat, timestamps, jobs

def get_append_stat(job_pkg_stat, timestamps, jobs, metrics, pkgs):
    # append process features
    items = []
    for timestamp in timestamps:
        for pkg in pkgs:
            for job in jobs:
                item = {'timestamp': timestamp, 'pkg_id': int(pkg), 'job': job}
                try:
                    selected = job_pkg_stat.loc[(timestamp, int(pkg), job),:]
                    value_data = dict(zip(selected.index.format(), selected))
                    item.update(value_data)
                except KeyError:
                    for metric in metrics:
                        item[metric] = 0
                items += [item]
    _append_stat = pd.DataFrame(items)
    append_scaler = MinMaxScaler()
    append_scaler.fit(_append_stat[metrics].values)
    return _append_stat, append_scaler

def get_append_x(_append_stat, timestamps, jobs, metrics, pkgs):
    x_values = None
    for pkg in pkgs:
        pkg_id = int(pkg)
        # selected specific package
        pkg_stat_values = _append_stat[_append_stat['pkg_id']==pkg_id].drop(columns=['pkg_id'])
        # sort by timestamp and job again
        pkg_stat_df = pkg_stat_values.sort_values(['timestamp', 'job']).drop(columns=['job']).set_index(['timestamp'])
        pkg_stat_values = pkg_stat_df.values
        
        reshaped_values = pkg_stat_values.reshape([len(timestamps), len(jobs), len(metrics)])[1:]
        if x_values is None:
            x_values = reshaped_values
        else:
            x_values = np.append(x_values, reshaped_values, axis=0)
    return x_values

def get_append_y(pkgs, _package_power):
    y_values = None
    for pkg in pkgs:
        pkg_id = int(pkg)
        selected_row = _package_power[_package_power['pkg_id']==pkg_id]
        values = selected_row['pkg'].values
        if y_values is None:
            y_values = values
        else:
            y_values = np.append(y_values, values, axis=0)
    return y_values

def get_append_frequency(_cpu_frequency, pkgs, _package_power):
    timestamps = pd.unique(_package_power['timestamp'])
    freq_values = None
    for pkg in pkgs:
        pkg_id = int(pkg)
        # selected specific package
        pkg_freq_values = _cpu_frequency[_cpu_frequency['pkg_id']==pkg_id].drop(columns=['pkg_id'])
        cpus = pd.unique(pkg_freq_values['cpu'])
        # sort by timestamp and job again
        pkg_freq_values = pkg_freq_values.sort_values(['timestamp', 'cpu']).drop(columns=['cpu']).set_index(['timestamp']).values
        reshaped_values = pkg_freq_values.reshape([len(timestamps)+1, len(cpus), 1])[1:]
        if freq_values is None:
            freq_values = reshaped_values
        else:
            freq_values = np.append(freq_values, reshaped_values, axis=0)
    freq_scaler = MinMaxScaler()
    freq_scaler.fit(_cpu_frequency[['freq_hz']].values)
    return freq_values, freq_scaler

def get_aggr_stat(_pod_cpu_stat, metrics):
    groupped_pod_cpu_stat = _pod_cpu_stat[['timestamp', 'pkg_id']+list(metrics)].groupby(['timestamp', 'pkg_id'])
    sum_df = groupped_pod_cpu_stat.sum()
    mean_df = groupped_pod_cpu_stat.mean()
    std_df = groupped_pod_cpu_stat.std()
    min_df = groupped_pod_cpu_stat.min()
    max_df = groupped_pod_cpu_stat.max()
    aggr_df = sum_df.join(mean_df, lsuffix='_sum', rsuffix='_mean')
    aggr_df = aggr_df.join(std_df, rsuffix='_std')
    aggr_df = aggr_df.join(min_df, rsuffix='_min')
    aggr_df = aggr_df.join(max_df, rsuffix='_max')
    aggr_df = aggr_df.sort_index(level='pkg_id')
    aggr_df.reset_index()
    aggr_scaler = MinMaxScaler()
    aggr_scaler.fit(aggr_df.reset_index()[aggr_df.columns].values)
    return aggr_df, aggr_scaler

def get_append_data(_pod_cpu_stat, package_power, cpu_frequency, pkg_cpu, metrics, pkg_map_json):
    pkgs = pkg_map_json.keys()
    _package_power = package_power.reset_index().sort_values(['timestamp'])
    _cpu_frequency = cpu_frequency.join(pkg_cpu).reset_index()

    job_pkg_stat, timestamps, jobs = get_job_stat(_pod_cpu_stat, metrics)
    _append_stat, append_scaler = get_append_stat(job_pkg_stat, timestamps, jobs, metrics, pkgs)
    x_values = get_append_x(_append_stat, timestamps, jobs, metrics, pkgs)
    y_values = get_append_y(pkgs, _package_power)
    freq_values, freq_scaler = get_append_frequency(_cpu_frequency, pkgs, _package_power)

    metadata = dict()
    metadata['jobs'] = list(jobs)
    metadata['metrics'] = list(metrics)

    return x_values, y_values, freq_values, metadata, append_scaler, freq_scaler

def get_aggr_data(_pod_cpu_stat, package_power, cpu_frequency, pkg_cpu, metrics, pkg_map_json):
    aggr_df, aggr_scaler = get_aggr_stat(_pod_cpu_stat, metrics)
    freq_scaler = MinMaxScaler()
    mean_freq_df = cpu_frequency.join(pkg_cpu).reset_index().groupby(['timestamp', 'pkg_id']).mean().drop(columns=['cpu'])
    freq_scaler.fit(mean_freq_df)
    full_df = aggr_df.join(package_power).join(mean_freq_df).dropna()
    x_values = full_df[aggr_df.columns].values
    y_values = full_df['pkg'].values
    freq_values = full_df[['freq_hz']].values

    metadata = dict()
    metadata['metrics'] = list(aggr_df.columns)

    return x_values, y_values, freq_values, metadata, aggr_scaler, freq_scaler

def extract(output_folders, fe, get_method, _pod_cpu_stat, metrics, package_power, cpu_frequency, pkg_cpu, pkg_map_json):
    x_values, y_values, freq_values, metadata, scaler, freq_scaler = get_method(_pod_cpu_stat, package_power, cpu_frequency, pkg_cpu, metrics, pkg_map_json)
    save_data(output_folders, fe, x_values, y_values, freq_values, metadata, scaler, freq_scaler)

def save_pod_cpu_stat(workload, _pod_cpu_stat, metrics):
    output_folder = get_workload_path(workload)
    pod_cpu_stat_file = output_folder + "/" + "pod_cpu_stat.csv"
    _pod_cpu_stat[['timestamp', 'pkg_id', 'pod_name']+list(metrics)].to_csv(pod_cpu_stat_file, index=False)

def save_cpu_frequency(workload, cpu_frequency, pkg_cpu):
    output_folder = get_workload_path(workload)
    _cpu_frequency = cpu_frequency.join(pkg_cpu).reset_index()
    cpu_frequency_file = output_folder + "/" + "cpu_frequency.csv"
    _cpu_frequency.to_csv(cpu_frequency_file, index=False)

def save_package_power(workload, package_power):
    output_folder = get_workload_path(workload)
    _package_power = package_power.reset_index().sort_values(['timestamp'])
    package_power_file = output_folder + "/" + "package_power.csv"
    _package_power.to_csv(package_power_file, index=False)

def _transform_component(pod):
    for key in component_keys:
        if key in pod:
            return key
    print('cannot arange pod:', pod)
    return None

def get_full_pod_cpu_stat(_pod_cpu_stat):
    min_timestamp = min(_pod_cpu_stat['timestamp'])
    _pod_cpu_stat = _pod_cpu_stat[_pod_cpu_stat['timestamp'] != min_timestamp]
    _pod_cpu_stat['wl'] = _pod_cpu_stat['pod_name'].transform(_transform_component)
    _pod_cpu_stat.drop(columns=['pod_name'], inplace=True)
    return _pod_cpu_stat.copy()

def get_groupped_pod_cpu_stat(workload, _pod_cpu_stat):
    output_folder = get_workload_path(workload)
    groupped_filename = os.path.join(output_folder, 'full_groupped_pod_cpu_stat.csv')
    if os.path.exists(groupped_filename):
        full_groupped_pod_cpu_stat = pd.read_csv(groupped_filename)
    else:
        full_groupped_pod_cpu_stat = get_full_pod_cpu_stat(_pod_cpu_stat).sort_values(['pkg_id', 'timestamp'])
        full_groupped_pod_cpu_stat.to_csv(groupped_filename, index=False)
    return full_groupped_pod_cpu_stat

component_keys = ['coremark', 'tpcc', 'cpe', 'grafana', 'prometheus-prometheus', 'alertmanager', \
    'dns', 'kepler', 'kubevirt', 'node-resolver', 'router', 'service', 'system_processes', 'blackbox', \
        'kube-state', 'kube-flannel', 'prometheus-k8s', 'prometheus-operator', 'node-exporter', \
            'prometheus-adapter', 'cockroachdb']

def get_wl_dataset(workload, _pod_cpu_stat):
    output_folder = get_workload_path(workload)
    wl_data_folder = os.path.join(output_folder, 'wl_data')
    if not os.path.exists(wl_data_folder):
        os.mkdir(wl_data_folder)
    full_groupped_pod_cpu_stat = get_groupped_pod_cpu_stat(workload, _pod_cpu_stat)
    ts_pkg = full_groupped_pod_cpu_stat[['timestamp', 'pkg_id']]
    ts_pkg = ts_pkg.set_index(['timestamp', 'pkg_id'])
    wls = pd.unique(full_groupped_pod_cpu_stat['wl'])
    print(wls)
    wl_dataset = dict()
    for key in component_keys:
        if key not in wls:
            continue
        wl_data_filename = os.path.join(wl_data_folder, '{}.csv'.format(key))
        if os.path.exists(wl_data_filename):
            wl_dataset[key] = pd.read_csv(wl_data_filename).set_index(['pkg_id', 'timestamp']) 
        else:
            wl_df = full_groupped_pod_cpu_stat[full_groupped_pod_cpu_stat['wl'] == key].drop(columns=['wl'])
            wl_df = ts_pkg.join(wl_df.set_index(['timestamp', 'pkg_id'])).fillna(0).reset_index()
            wl_dataset[key] = wl_df.set_index(['pkg_id', 'timestamp'])
            wl_dataset[key].to_csv(wl_data_filename)
    return wl_dataset, full_groupped_pod_cpu_stat

import sys

def process(workload, output_folders):
    pkg_cpu, pkg_map_json = load_pkg_cpu()
    sample_data = load_sample_data(workload)

    pod_cpu_stat = get_pod_cpu_stat(sample_data, pkg_cpu)
    metrics = pod_cpu_stat.drop(columns=['pkg_id']).columns
    _pod_cpu_stat = pod_cpu_stat.reset_index()
    package_power = get_package_power(sample_data, pkg_map_json)
    cpu_frequency = get_cpu_frequency(sample_data)

    save_pod_cpu_stat(workload, _pod_cpu_stat, metrics)
    save_cpu_frequency(workload, cpu_frequency, pkg_cpu)
    save_package_power(workload, package_power)
    # uncomment this line if want wl_data
    # get_wl_dataset(workload, _pod_cpu_stat)

    for fe in feature_extracting_methods:
        get_method = getattr(sys.modules[__name__], 'get_{}_data'.format(fe))
        extract(output_folders, fe, get_method, _pod_cpu_stat, metrics, package_power, cpu_frequency, pkg_cpu, pkg_map_json)

if __name__ == '__main__':
    workload = sys.argv[1]
    output_folders = new_output_folders(workload)
    process(workload, output_folders)