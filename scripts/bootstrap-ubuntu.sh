#!/usr/bin/env bash
# For an explicitly approved Ubuntu 24.04 host. Does not expose an app or copy secrets.
set -euo pipefail
if [[ "${1:-}" != "--approved" ]]; then
  echo "Usage: sudo scripts/bootstrap-ubuntu.sh --approved (review host changes first)"
  exit 2
fi
test "$(id -u)" = 0
. /etc/os-release
test "$ID" = ubuntu
test "$VERSION_ID" = 24.04
apt-get update
apt-get install -y ca-certificates curl git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
architecture="$(dpkg --print-architecture)"
echo "deb [arch=$architecture signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
install -d -m 0750 /opt/flowstate
echo "Docker ready. Configure a deployment user and secrets explicitly; Docker group access is root-equivalent."
