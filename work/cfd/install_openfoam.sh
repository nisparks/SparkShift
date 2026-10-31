#!/bin/bash
# Install the newest ESI OpenFOAM release from the official dl.openfoam.com apt repository.
set -e
export DEBIAN_FRONTEND=noninteractive
curl -s https://dl.openfoam.com/add-debian-repo.sh | bash > /tmp/addrepo.log 2>&1
apt-cache search --names-only '^openfoam2[0-9]+-default$' | sort
v=$(apt-cache search --names-only '^openfoam2[0-9]+-default$' | sort | tail -1 | cut -d' ' -f1)
echo "INSTALLING $v"
apt-get install -y "$v" > /tmp/of_install.log 2>&1 || { tail -20 /tmp/of_install.log; exit 1; }
tail -2 /tmp/of_install.log
ls /usr/lib/openfoam
