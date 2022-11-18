from prometheus_api_client import PrometheusConnect
import datetime
import json

top_folder = "query_output"

metric_prefix = "kepler_"

step = "3"
params = None

UTC_OFFSET_TIMEDELTA = datetime.datetime.utcnow() - datetime.datetime.now()

def _range_queries(prom, metric_list, start, end):
    global metrics, step, params 
    response = dict()
    for metric in metric_list:
        response[metric] = prom.custom_query_range(metric, start, end, step, params)
    return response


def query(prom, metric_list, start, end, offset=0):
    print("collecting from {0} to {1}".format(start, end))
    response = _range_queries(prom, metric_list, start - UTC_OFFSET_TIMEDELTA, end - UTC_OFFSET_TIMEDELTA)
    return response

def save(workload, response, level):
    output_flename = "{0}/{2}/{1}.json".format(top_folder, workload,level)
    with open(output_flename, "w") as outfile:
        json.dump(response, outfile)


import sys
import yaml
from yaml.loader import SafeLoader

STATUS_FOLDER = "../../tool/status"
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
    vm_prom = PrometheusConnect(url ="http://127.0.0.1:9090", disable_ssl=True)
    bm_prom = PrometheusConnect(url ="http://127.0.0.1:9091", disable_ssl=True)
    vm_metric_list = [m for m in vm_prom.all_metrics() if metric_prefix in m]
    bm_metric_list = [m for m in bm_prom.all_metrics()if metric_prefix in m]
    vm_metric_list += [m for m in vm_metric_list if "coremark" in m]
    print("VM metrics:", vm_metric_list)
    print("BM metrics:", bm_metric_list)

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

    vm_response = query(vm_prom, vm_metric_list, start, end)
    bm_response = query(bm_prom, bm_metric_list, start, end)
    save(workload, vm_response, "vm")
    save(workload, bm_response, "bm")
