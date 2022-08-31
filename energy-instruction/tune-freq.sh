#!/bin/bash
# pre-requisite
# sysbench: yum install https://repo.percona.com/yum/release/8/RPMS/x86_64/sysbench-1.0.20-6.el8.x86_64.rpm
SLEEP=30
RUNTIME=120
TOTAL=`expr ${SLEEP} + ${RUNTIME}`

STEP=5

NUM_CPU=$(cat /proc/cpuinfo |grep processor |awk '{print $3}'|sort -g|tail -1)
CPU_STEP=`expr ${NUM_CPU} / ${STEP}`

FREQ_LOW=$(cpupower frequency-info -l|tail -1|awk '{print $1}')
FREQ_HIGH=$(cpupower frequency-info -l|tail -1|awk '{print $2}')
FREQ_RANGE=`expr ${FREQ_HIGH} - ${FREQ_LOW} `
FREQ_STEP=`expr ${FREQ_RANGE} / ${STEP}`
FREQ_UNIT="MHz"

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

for THREADS in $(seq ${CPU_STEP} ${CPU_STEP} ${NUM_CPU})
do
    for II in $(seq 0 ${STEP})
    do
        FREQ=`expr ${FREQ_LOW} + ${II} \* ${FREQ_STEP}`
        echo "THREADS ${THREADS}, FREQ ${FREQ}"
        run_test
        power_saving
        curl "http://${IP}:9090/api/v1/query?query=node_energy_stat[${TOTAL}s]" | jq .data.result[].metric > result/freq-test-${THREADS}-${FREQ}.json
        cat result/freq-test-${THREADS}-${FREQ}.json | jq -r '[(.node_curr_energy_in_core|tonumber) / (.curr_cpu_instructions|tonumber)]' |grep -e [0-9] > result/energy_per_instr-${THREADS}-${FREQ}.dat
        cat result/freq-test-${THREADS}-${FREQ}.json | jq -r '[(.node_curr_energy_in_core|tonumber)]' |grep -e [0-9] > result/energy-${THREADS}-${FREQ}.dat
        cat result/freq-test-${THREADS}-${FREQ}.json | jq -r '[(.node_curr_cpu_instructions|tonumber)]' |grep -e [0-9] > result/instruction-${THREADS}-${FREQ}.dat
    done    
done