from prometheus_api_client import PrometheusConnect
import datetime
import json

top_folder = "query_output"

metrics = [
    "pod_energy_stat",
    "node_hwmon_power_average_watt",
    "node_cpu_scaling_frequency_hertz",
    "node_package_energy_joule",
    "node_package_energy_millijoule",
    "pod_cpu_cpu_time_us"
]

step = "3"
params = None
metric_list = []

UTC_OFFSET_TIMEDELTA = datetime.datetime.utcnow() - datetime.datetime.now()

def _range_queries(start, end):
    global metrics, step, params, metric_list
    response = dict()
    for metric in metrics:
        if metric not in metric_list:
            print("{0} not in metric list".format(metric))
        else:
            response[metric] = prom.custom_query_range(metric, start, end, step, params)
    return response


def query(start, end, offset=0):
    print("collecting from {0} to {1}".format(start, end))
    response = _range_queries(start - UTC_OFFSET_TIMEDELTA, end - UTC_OFFSET_TIMEDELTA)
    return response

def save(workload, response):
    output_flename = "{0}/{1}.json".format(top_folder, workload)
    with open(output_flename, "w") as outfile:
        json.dump(response, outfile)


import sys
import yaml
from yaml.loader import SafeLoader

STATUS_FOLDER = "../workload/status"
def extract_time(workload):
    file_name = "{0}/{1}.yaml".format(STATUS_FOLDER, workload)
    with open(file_name, "r") as f:
        data = yaml.load(f, Loader=SafeLoader)
        start_str = data["metadata"]["creationTimestamp"]
        start = datetime.datetime.strptime(start_str, '%Y-%m-%dT%H:%M:%SZ')
        end_str = data["status"]["results"][-1]["repetitions"][-1]["pushedTime"].split(".")[0]
        end = datetime.datetime.strptime(end_str, '%Y-%m-%d %H:%M:%S')
    return start, end

def convert_time(timestr):
    datetime_object = datetime.datetime.strptime(timestr, '%Y-%m-%d %H:%M:%S') # in UTC
    return datetime_object - UTC_OFFSET_TIMEDELTA

if __name__ == "__main__":
    prom = PrometheusConnect(url ="http://127.0.0.1:9091", disable_ssl=True)
    metric_list = prom.all_metrics()
    metrics += [m for m in metric_list if "coremark" in m]
    print(metrics)

    if len(sys.argv) < 2:
        print("enter workload status.")
        exit()

    workload = sys.argv[1]
    if "idle" in workload:
        try:
            collect_duration = int(sys.argv[2])
        except Exception as e:
            print("enter time duration (s) for idle: ", e)
            exit()
        end = datetime.datetime.utcnow()
        start = end - datetime.timedelta(seconds=collect_duration)
    else:
        start, end = extract_time(workload)

    response = query(start, end)
    save(workload, response)
