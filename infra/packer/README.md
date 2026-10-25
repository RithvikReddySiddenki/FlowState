# Immutable Docker host image

Run from this directory: `packer init .`, `packer fmt -check .`, then
`packer validate .` where credentials/plugins permit. Syntax-only validation
does not mean an AMI was built. NEVER run packer build without explicit approval:
it creates paid temporary EC2, storage and resulting AMI snapshots.

The image installs Ubuntu security updates, Docker, Compose and deployment
prerequisites. It contains no application environment, OAuth secrets or user data.
Supply the resulting reviewed AMI ID to the simple Terraform ami_id variable.
Terraform handles instances/networking, Ansible handles runtime configuration,
and reviewed deployment releases supply the application. No cloud image build
has been performed. The image prepares sysstat and Prometheus node exporter;
the exporter is disabled in the image. At runtime bind it to an explicitly
approved private interface and restrict scraping before enabling its service.
No account-specific monitoring credentials are baked into the image.
