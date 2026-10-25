# Configuration management

Controller: Linux/WSL with Ansible; target: Ubuntu 24.04 with working key-based
SSH and sudo. Start with `ansible-playbook -i inventory.example.yml site.yml
--syntax-check`. Review the inventory/host keys before any actual run.

Roles install Docker from its signed apt repository, enable updates, configure
key-only SSH, create deployment directories and handle services. The datastore
role binds PostgreSQL/Redis only to an explicitly supplied private address. The
automatic application deployment role deliberately requires flowstate_lab=true:
it uses synthetic lab variables and a private database VM, not real Gmail data.
State checks and registered configuration changes avoid unnecessary restarts.
Never disable protected mode or use these synthetic settings on a public network.

Production use requires a separately reviewed inventory, least-privilege network
policy, pinned release, secure environment delivery through Ansible Vault or a
secret manager, backup/migration approval and the deployment runbook. Keep vault
files/keys outside tracked source; sensitive templates use no_log and mode 0600.
Do not copy real environment files through shared Vagrant folders. The monitoring
role provisions private Prometheus/Grafana and scrapes the application VM's
private API/operations metrics. Syntax checks pass for all roles. Actual VM
provisioning and a second-run idempotence check require Vagrant/VirtualBox and
remain unverified; do not infer runtime success from syntax checks.
