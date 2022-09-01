#!/bin/bash
set -e 

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

echo -n "Utilization,"
for II in $(seq 0 ${STEP})
do  
    FREQ=`expr ${FREQ_LOW} + ${II} \* ${FREQ_STEP}`
    echo -n ${FREQ}"MHz,"
done
echo

for THREADS in $(seq ${CPU_STEP} ${CPU_STEP} ${NUM_CPU})
do
    Utilization=`expr ${THREADS} \* 100 / ${NUM_CPU}`
    echo -n ${Utilization}"%"
    OUTPUT=""
    for II in $(seq 0 ${STEP})
    do
        FREQ=`expr ${FREQ_LOW} + ${II} \* ${FREQ_STEP}`

        LINES=$(cat result/energy_per_instr-${THREADS}-${FREQ}.dat|wc -l)
        MEAN_LINES=`expr ${LINES} / 2`
        MEAN=$(cat result/energy_per_instr-${THREADS}-${FREQ}.dat|sort -g |head -${MEAN_LINES} |tail -1)
        #echo "THREADS ${THREADS}, FREQ ${FREQ} MEAN ${MEAN}"
        OUTPUT=${OUTPUT}","${MEAN}
        #echo ${OUTPUT}
    done
    echo ${OUTPUT}
done