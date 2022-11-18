# Data Description
```bash
.
├── README.md
├── common.py
├── csv
│   ├── cpu_frequency.csv
│   ├── node_total_power.csv
│   ├── package_power.csv
│   └── pod_cpu_stat.csv
├── pkg_map.json
├── query.py
└── query_output
    ├── bm
    │   └── coremark_4threads_to_32threads_5rep_vm.json # raw prometheus query output from Kepler on BM
    └── vm
        └── coremark_4threads_to_32threads_5rep_vm.json # raw prometheus query output from Kepler on VM
``` 
The data here can be used for training node-level power (both total and components) from hardware counter features and frequency feature. 

More data can be extracted from query_output folder. Check function *read_json* from [common.py](common.py).


