#!/bin/bash
set -e

# Arda OS: Sovereign Provisioner v4.1
# This script runs inside the VM during the Packer build.

echo "ARDA: Starting Sovereign Provisioning..."

# 1. Update and Install Core Dependencies
sudo apt-get update
sudo apt-get install -y \
    python3.13 python3.13-venv python3.13-dev \
    libbpf-dev python3-bpfcc bpfcc-tools \
    gsettings-desktop-schemas gnome-backgrounds \
    chromium x11-xserver-utils

# 2. Setup the Arda Project
echo "ARDA: Deploying Arda OS Source..."
sudo mkdir -p /opt/arda_os
sudo cp -r /tmp/arda_os/* /opt/arda_os/
sudo chown -R arda:arda /opt/arda_os

# 3. Configure the 'arda' user environment
echo "ARDA: Configuring Sovereign User (arda)..."
# Set Arda Wallpaper
WALLPAPER_PATH="/opt/arda_os/docs/assets/wallpaper.png"
sudo -u arda gsettings set org.gnome.desktop.background picture-uri "file://$WALLPAPER_PATH"
sudo -u arda gsettings set org.gnome.desktop.background picture-uri-dark "file://$WALLPAPER_PATH"

# 4. Configure GDM3 Auto-login
echo "ARDA: Enabling Passwordless Auto-login..."
sudo sed -i 's/#  AutomaticLoginEnable = true/  AutomaticLoginEnable = true/g' /etc/gdm3/daemon.conf
sudo sed -i 's/#  AutomaticLogin = user1/  AutomaticLogin = arda/g' /etc/gdm3/daemon.conf

# 5. Enable Arda Sovereign Guard Service
echo "ARDA: Arming the Ring-0 Guard..."
# Inject the correct configuration into the service file
cat <<EOF > /tmp/arda-lsm-guard.service
[Unit]
Description=Arda Sovereign Law Enforcement (BPF Guard)
DefaultDependencies=no
After=local-fs.target
Before=sysinit.target

[Service]
Type=simple
Environment=ARDA_SOVEREIGN_MODE=1
ExecStart=/usr/bin/python3.13 /opt/arda_os/arda_os/os_enforcement_service.py
Restart=always
CapabilityBoundingSet=CAP_SYS_ADMIN CAP_BPF CAP_DAC_OVERRIDE
AmbientCapabilities=CAP_SYS_ADMIN CAP_BPF CAP_DAC_OVERRIDE

[Install]
WantedBy=sysinit.target
EOF
sudo mv /tmp/arda-lsm-guard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable arda-lsm-guard.service

# 6. Capture Fine-Tuning: Syncing Manifest
echo "ARDA: Initializing Sovereign Manifest..."
cd /opt/arda_os/arda_os
python3.13 -c "import os; from os_enforcement_service import get_os_enforcement_service; svc = get_os_enforcement_service(); print('Sovereign Manifest Initialized')"

# 7. Cleanup
sudo rm -rf /tmp/arda_os
echo "ARDA: Sovereign Provisioning Complete. Arda remains."
