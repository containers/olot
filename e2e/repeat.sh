#!/bin/bash
set -e
set -o xtrace

while ! $@ ; do echo "Retrying..."; sleep 5; done
