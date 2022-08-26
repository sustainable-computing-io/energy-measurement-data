# Data Description

1. The workloads run on top of [CPE](https://github.com/IBM/cpe-operator) benchmark operator.
The output from CPE operator is in `workload-status` folder.
2. `query.py` is executed based on the name of workload in `workload-status` to query the prometheus during the period that the workload was running. The output is in `query_output` folder with the filename `<workload>.json`
3. `feature_extract.py` is executed to pre-process the `query_output` and save under the `model_data_input`.
   ```bash
   python feature_extract.py <workload>
   ```
    - pod_cpu_stat: sum stats for each (timestamp, pod, pkgid)
    - aggr: aggregated input features (x), package power label(y), min-max scaler for x, average CPU frequency (freq), min-max scaler for freq, metadata.json (metric list)
    - append: appended input features (x), package power label(y), min-max scaler for x, average CPU frequency (freq), min-max scaler for freq, metadata.json (metric list, podlist)
    - cpu_frequency.csv: frequency for each (timestamp,cpu,pkg_id)
    - package_power.csv: package power for each (timestamp, pkg_id)
    - full_groupped_pod_cpu_stat.csv: sum stats for each (timestamp, wl, pkgid); wl = groupped pod by prefix
    - wl_data: separated stats for each wl for each (timestamp, pkgid)

### Benchmark and Workload Naming
There are 2 benchmarks:
- coremark: Coremark (CPU intensive)
- tpcc: TPCC on cockroach DB (Memory and I/O intensive)

There are 4 CPU frequency governors for Coremark benchmark.
- conservative
- ondemand
- performance
- powersave

*only ondemand is experimented for TPCC*

```
workload: <workload-prefix>_<governor>
workload_predix: <benchmark>_<start iterated param>_<end iterated param>_<rep num>rep
```

  ** As query output of tpcc is too large to push to github repo, it is not available here. **