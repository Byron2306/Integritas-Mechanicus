#!/bin/bash
set -e

echo "ARDA OS: Starting Sovereign OVA Build v4.1..."

# 1. Dependency Check
if ! command -v packer &> /dev/null; then
    echo "ERROR: Packer not found. Please install it from https://www.packer.io/"
    exit 1
fi

if ! command -v vboxmanage &> /dev/null; then
    echo "ERROR: VirtualBox not found. This build requires vboxmanage."
    exit 1
fi

# 2. Initialize Packer
echo "ARDA: Initializing Packer plugins..."
packer init packer/packer.pkr.hcl

# 3. Build the OVA
echo "ARDA: Building Sovereign OVA (This will take 15-30 minutes)..."
packer build packer/packer.pkr.hcl

echo "ARDA: Sovereign OVA complete. File available in output-arda-os/"
