#!/bin/bash

# from https://kserve.github.io/website/latest/modelserving/storage/oci/#enabling-modelcars
# Script to enable Modelcars
# Fetch the current storageInitializer configuration
config=$(kubectl get configmap inferenceservice-config -n kserve -o jsonpath='{.data.storageInitializer}')
# Enable modelcars and set the UID for the containers to run (required for minikube)
newValue=$(echo $config | jq -c '. + {"enableModelcar": true, "uidModelcar": 1010}')

# Create a temporary directory for the patch file
tmpdir=$(mktemp -d)
cat <<EOT > $tmpdir/patch.txt
[{
  "op": "replace",
  "path": "/data/storageInitializer",
  "value": '$newValue'
}]
EOT

# Apply the patch to the ConfigMap
kubectl patch configmap -n kserve inferenceservice-config --type=json --patch-file=$tmpdir/patch.txt

# Restart the KServe controller to apply changes
kubectl delete pod -n kserve -l control-plane=kserve-controller-manager
