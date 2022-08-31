#!/bin/bash
SLEEP=30
RUNTIME=120
TOTAL=`expr ${SLEEP} + ${RUNTIME}`

function run_test () {
    cpupower set -b 0
    cpupower frequency-set -d ${FREQ} 2>&1 > /dev/null
    cpupower frequency-set -u ${FREQ} 2>&1 > /dev/null
    sleep ${SLEEP}
    echo ${FREQ} ${THREADS}
    sysbench cpu --threads=${THREADS}  --time=${RUNTIME} run 2>&1 > /dev/null
}

function power_saving () {
    cpupower set -b 15
    cpupower frequency-set -d 800MHZ 2>&1 > /dev/null
    cpupower frequency-set -u 800MHZ 2>&1 > /dev/null
    sleep ${SLEEP}
}

cpupower frequency-set -g performance 2>&1 > /dev/null

mkdir -p result
export IP=$(kubectl get svc -n monitoring prometheus-k8s -ojsonpath='{.spec.clusterIP}')

for THREADS in 8 16 32
do
    for FREQ in "800MHZ" "1000MHz" "1500MHz" "2000MHz" "2500MHz"
    do
        run_test
        power_saving
        curl "http://${IP}:9090/api/v1/query?query=node_energy_stat[${TOTAL}s]" | jq .data.result[].metric > result/freq-test-${THREADS}-${FREQ}.json
        cat result/freq-test-${THREADS}-${FREQ}.json | jq -r '[(.curr_energy_in_core|tonumber) / (.curr_cpu_instructions|tonumber)]' |grep -e [0-9] > result/energy_per_instr-${THREADS}-${FREQ}.dat
        cat result/freq-test-${THREADS}-${FREQ}.json | jq -r '[(.curr_energy_in_core|tonumber)]' |grep -e [0-9] > result/energy-${THREADS}-${FREQ}.dat
        cat result/freq-test-${THREADS}-${FREQ}.json | jq -r '[(.curr_cpu_instructions|tonumber)]' |grep -e [0-9] > result/instruction-${THREADS}-${FREQ}.dat
    done    
done