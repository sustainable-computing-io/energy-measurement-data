# CPE Operator to Collect Cloud-native Workload Data
### 1. Deploy CPE Operator
```bash
kubectl apply -f cpe_deploy.yaml
```
### 2. Deploy benchmarks
2.1 Coremark
Deploy operator
```bash
kubectl create -f coremark/cpe_v1_none_operator.yaml
```

Deploy benchmark
```bash
kubectl create -f coremark/cpe_v1_coremark.yaml
```

Check benchmark status
```bash
export KUBECONFIG_FILE=~/.kube/config
./cpec-$(go env GOOS)-$(go env GOARCH) status
```

Save (the benchmark file will be in *status* folder)
```bash
chmod +x save.sh; mkdir -p status
./save.sh coremark
```

2.2. TPCC

Deploy operator
```bash
kubectl create -f tpcc/cpe_v1_cockroachoperator_helm.yaml
kubectl wait pod -n cockroach-operator-system cockroach-release-cockroachdb-0 --for condition=ready --timeout=90s
```

Load data (this step could take more than 10 minutes)
```bash
kubectl create -f tpcc/tpcc_load_job.yaml
kubectl wait job -n cockroach-operator-system tpcc-data-load --for condition=complete --timeout=-1s
kubectl delete -f tpcc/tpcc_load_job.yaml
```

Deploy benchmark
```bash
kubectl create -f tpcc/cpe_v1_cockroach_tpcc.yaml
```

Check benchmark status
```bash
export KUBECONFIG_FILE=~/.kube/config
./cpec-$(go env GOOS)-$(go env GOARCH) status
```

Save (the benchmark file will be in *status* folder)
```bash
chmod +x save.sh; mkdir -p status
./save.sh tpcc
```

### 3. Make query based on saved benchmark CR

Use [query.py](../data/netsres59/query.py)
```bash
python query.py <saved workload name>
```

The result will be in `query_output` folder.

### Clean up benchmark and benchmark operator
> Note that, there is no need to clean up benchmark operator for every benchmark deployment.
You can delete and redeploy only the benchmark CR.

- Coremark Benchmark
```bash
kubectl delete -f coremark/cpe_v1_coremark.yaml
```
- Default Job Operator and PVC
```bash
kubectl delete -f coremark/cpe_v1_none_operator.yaml
```
- TPCC Benchmark
```bash
kubectl delete -f tpcc/cpe_v1_cockroach_tpcc.yaml
```
- CockroachDB Operator and PVC
```bash
kubectl delete -f tpcc/cpe_v1_cockroachoperator_helm.yaml
kubectl delete pvc -n cockroach-operator-system --all
```

### Clean up CPE operator
```bash
kubectl delete -f cpe_deploy.yaml
```