#!/bin/bash

if [[ -n "$LOCAL" ]]; then
    CLUSTER_NAME="${CLUSTER_NAME:-olot-e2e}"

    echo 'Creating local Kind cluster for E2E testing...'

    if [[ $(kind get clusters || false) =~ $CLUSTER_NAME ]]; then
        echo 'Cluster already exists, skipping creation'

        kubectl config use-context "kind-$CLUSTER_NAME"
    else
        kind create cluster -n "$CLUSTER_NAME"
    fi
fi
