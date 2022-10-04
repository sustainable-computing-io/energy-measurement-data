#! /bin/bash

if [[ -z $1 ]]; then
    echo "Must input benchmark"
    exit
fi

BENCHMARK=$1
GOVERNOR=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
FIRST_VALUE=$(oc get benchmark $BENCHMARK -ndefault -ojson|jq -r .spec.iterationSpec.iterations[0].values[0])
LAST_VALUE=$(oc get benchmark $BENCHMARK -ndefault -ojson|jq -r .spec.iterationSpec.iterations[0].values[-1])
REPETITION=$(oc get benchmark $BENCHMARK -ndefault -ojson|jq -r .spec.repetition)rep
WORKLOAD_NAME=${BENCHMARK}_${FIRST_VALUE}_to_${LAST_VALUE}_${REPETITION}_${GOVERNOR}
echo $WORKLOAD_NAME


kubectl get benchmark $BENCHMARK -n default -oyaml > status/${WORKLOAD_NAME}.yaml