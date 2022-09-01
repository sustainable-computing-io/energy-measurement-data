# Measure Energy per Instruction 

This experiment uses metrics exported by Kepler to measure energy consumed per CPU instruction during the sampling interval.

# Setup

The workload is `sysbench cpu`. The script is [tune-freq.sh](./tune-freq.sh)

By varying the number of threads, the workload generate a controlled CPU utilization.

The CPU frequency managed by `cpupower`. The lower and upper frequency are set the same so the CPU cores are at a controlled levels.

There are ramping up and cooling off period during the workload run. After each run, the metrics are scrapped and energy per instruction is calculated.

# Report
The script [energy-per-instruction.sh](./energy-per-instruction.sh) extracts the data and generates a csv based report, detailing the energy per instruction at different CPU frequency and utilization.

# Result
A test run on an 64 core Intel Cascade Lake CPU is
```csv
CPU Utilization,1000000MHz,1580000MHz,2160000MHz,2740000MHz,3320000MHz,3900000MHz,
18%, 8.964693944309595e-09, 7.330685186394104e-09, 6.345580272493673e-09, 7.922615058173735e-09, 7.572360310942498e-09, 7.688297449127322e-09
37%, 5.640315330946943e-09, 4.156745919493822e-09, 3.835792922910084e-09, 5.075587831473748e-09, 5.4059828535545895e-09, 5.347693749298132e-09
56%, 4.540180409072492e-09, 3.513391383449346e-09, 3.153159691929021e-09, 3.80619143755373e-09, 4.0100791491027005e-09, 4.0167699027840384e-09
75%, 3.659826288548835e-09, 3.078686859669299e-09, 2.8635293219772927e-09, 3.4297377210172907e-09, 3.6983637483232817e-09, 3.6233803775590008e-09
93%, 3.663888050996792e-09, 2.68130182828064e-09, 2.703343654078494e-09, 3.274980653497776e-09, 3.5996814255866325e-09, 3.2136384704695905e-09
```


