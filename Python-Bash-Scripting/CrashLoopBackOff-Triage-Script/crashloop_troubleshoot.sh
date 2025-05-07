#!/bin/bash

echo "Scanning for pods in CrashLoopBackOff state across all namespaces..."

pods=$(kubectl get pods --all-namespaces --field-selector=status.phase!=Succeeded -o json | \
  jq -r '.items[] | select(.status.containerStatuses[]?.state.waiting?.reason == "CrashLoopBackOff") |
         [.metadata.name, .metadata.namespace] | @tsv')

if [[ -z "$pods" ]]; then
  echo "✅ No CrashLoopBackOff pods found."
  exit 0
fi

echo -e "Found pods in CrashLoopBackOff:\n"

while IFS=$'\t' read -r pod namespace; do
  echo "🔸 Pod: $pod"
  echo "   Namespace: $namespace"

  # Get container info
  containers=$(kubectl get pod "$pod" -n "$namespace" -o json | jq -r '.spec.containers[] | [.name, .image] | @tsv')

  while IFS=$'\t' read -r cname cimage; do
    echo "   Container: $cname"
    echo "   Image: $cimage"
    echo "   Logs (last 10 lines):"
    kubectl logs "$pod" -n "$namespace" -c "$cname" --tail=10 2>&1 | sed 's/^/     /'
    echo ""
  done <<< "$containers"

  echo "---------------------------------------------"
done <<< "$pods"





# NOTE: Make the script executable and run it:
# chmod +x crashloop_troubleshoot.sh
# ./crashloop_troubleshoot.sh


# NOTE: Requirements
# kubectl configured with access to the cluster
# jq installed for JSON parsing