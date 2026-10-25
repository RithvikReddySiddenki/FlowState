# Three-VM local lab

Requires Vagrant, VirtualBox and roughly 6 GB available VM RAM plus host overhead.
The configuration is not a claim that these tools are installed or VMs are running.
Check host-only subnet 192.168.56.0/24 for conflicts before `vagrant up`.

Nodes: application .10:8080, database .11:5432/6379 and monitoring .12. Shared
folders contain automation only, never local tokens, environment files or dumps.
Provisioning copies the read-only automation into each guest and runs Ansible.
Database starts first. The app uses the database VM's private IP; database/cache
containers bind only the host-only address. Host web forwarding is loopback
18081. `vagrant ssh application` provides SSH; `vagrant status` shows state.

After provisioning, test the app VM's `/api/health/ready`, then check database
container logs and private-IP connectivity if needed. No live Gmail is configured
in this lab. The application Git revision defaults to the development branch;
set flowstate_git_ref to a reviewed immutable commit for reproducible exercises.
Monitoring VM provisions Prometheus/Grafana, scraping API/operations metrics from
the application VM's host-only address. Grafana is private .12:3000 using the
explicitly synthetic lab password. This cross-VM setup is prepared but has not
been executed without Vagrant/provider availability.

Use `vagrant halt` to stop VMs. Destroying them removes guest-local volumes;
back up anything valuable and obtain explicit approval before destruction.
The original Docker Compose workflow remains independent.
