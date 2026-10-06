# Production Deployment Runbook

Deploy Corna from an empty cloud account to a running production environment.

**Expected time from zero infrastructure:** ~3–4 hours active work, including
verification.  
Allow additional elapsed time for DNS propagation.

---

## 1. Provision infrastructure

Ensure the cloud account does not contain conflicting resources, particularly
SSH keys or resources using the expected names.

```bash
terraform plan -var-file=tf.tfvars
terraform apply -var-file=tf.tfvars
```

Update local SSH config with the new VM IP address.

### Verify

- Terraform completes successfully.
- SSH works for all expected VM accounts.
- Cloud-init has completed:

```bash
journalctl -eu cloud-final
```

- All accounts have the expected groups, including `docker`:

```bash
id
```

- `psql` is installed.
- The VM can connect to the private PostgreSQL endpoint.
- The database is not accessible directly from the local/home network.

---

## 2. Provision PostgreSQL

Generate secure passwords for the Corna database users, for example with
`token_urlsafe(32)` or `token_urlsafe(48)`.

Update the required environment files with:

- private database host
- database credentials
- application/admin user credentials

The provider database defaults to `defaultdb`, which is currently assumed by
the provisioning script.

Run:

```bash
PATH="<path-to-pg-bin>:$PATH" ./infra/postgres/provision.sh remote
PATH="<path-to-pg-bin>:$PATH" ./infra/postgres/migration.sh remote
```

### Verify

From `psql`:

```text
\du
\l
\dt
```

Confirm:

- expected roles exist
- Corna database exists
- application tables exist
- All Corna database users can authenticate

---

## 3. Build and publish containers

Ensure Docker registry authentication works locally and for the required remote
accounts.

The release environment file must exist and contain all expected keys, even
when values are initially empty:

```text
BUILT_VERSION
BUILT_COMMIT
PUSHED_VERSION
PUSHED_COMMIT
DEPLOYED_VERSION
DEPLOYED_COMMIT
TLS_CERT_SECRET
TLS_KEY_SECRET
VAULT_PASSWORD_SECRET
```

Clean the local Docker environment before the release build:

```bash
docker system prune -a
```

Authenticate with the registry if required:

```bash
docker login registry.digitalocean.com
```

On the remote host, verify Docker access:

```bash
docker run --rm hello-world
```

Build and publish the release:

```bash
./infra/build.sh release
```

The production images must target `linux/amd64`.

Verify an image:

```bash
docker image inspect <image-sha>
```

Look for:

```text
"Architecture": "amd64"
```

Optionally verify it executes as amd64:

```bash
docker run --rm --platform linux/amd64 <image-sha> python --version
```

From the remote host, verify the exact release can be pulled:

```bash
docker pull registry.digitalocean.com/corna-container-registry/corna-nginx:<release>
```

### Verify

- build completes successfully
- expected images exist in the registry
- image sizes look reasonable
- images are `amd64`
- remote host can pull the release

---

## 4. Initialise Swarm and secrets

Initialise Swarm using the VM's **private IP**:

```bash
docker swarm init --advertise-addr <private-ip>
```

Verify:

```bash
docker info | grep Swarm
```

Expected:

```text
Swarm: active
```

Before creating secrets:

```bash
docker secret ls
```

For a new environment this should be empty.

Create the required secrets:

```bash
./infra/secrets.sh create-vault-password v1
./infra/secrets.sh create-tls <certificate-version>
```

For example:

```bash
./infra/secrets.sh create-tls 10_2026
```

### Verify

```bash
docker secret ls
```

Confirm all expected secrets exist.

---

## 5. Deploy

Run deployment with variables scoped directly to the command.

Do not export these into the existing shell environment; this avoids stale
environment variables affecting the deployment.

```bash
DEPLOY_HOST="cornaServer" \
CONFIG_FILE_PATH="<config-file-path>" \
CORNA_INVITE_APPROVAL_DIR="<approval-dir-path>" \
CORNA_RUNTIME_ASSET_DIR="<asset-dir-path>" \
DB_ADDRESS="<private-db-address>" \
REGISTRY="<registry-address>" \
./infra/deploy.sh
```

### Verify

On the remote host:

```bash
docker service ls
```

All expected services should reach their intended replica count.

For individual services:

```bash
docker service ps <service-name>
docker service logs <service-name>
```

Inspect running containers if required:

```bash
docker container ls
```

A healthy initial deployment should show the Corna application, invite
processor and nginx services running without restart/failure loops.

---

## 6. Verify application bootstrap

Verify that application startup/bootstrap has successfully exercised the
infrastructure.

Current bootstrap creates:

- System users
- Base avatars
- Merged theme images

The media assets produce original and thumbnail objects.

Expected S3 object count after bootstrap:

```text
2 * count(base avatars + theme images)
```

Confirm:

- expected users exist
- S3 contains the expected objects
- service logs are clean
- application can communicate with PostgreSQL
- application can communicate with S3

---

## 7. Verify public application

Wait for DNS changes to propagate if required.

Open the production domain over HTTPS.

Confirm:

- DNS resolves to the expected server
- TLS works
- nginx serves the application
- homepage loads successfully

For a full application release smoke test:

- create/login to a normal user account
- create a post
- verify the post is persisted and renders correctly
- include a media-backed post when the release needs explicit end-to-end S3
  verification

At this point the deployment is complete.

---

# Release checks

The deployment is considered successful when:

- Terraform infrastructure exists.
- VM bootstrap completes.
- PostgreSQL is reachable privately but not publicly.
- Database roles/schema are provisioned.
- Release images exist in the registry.
- Images use `linux/amd64`.
- Swarm is active.
- Required Docker secrets exist.
- All deployed services reach their expected replica counts.
- Bootstrap can write to PostgreSQL and S3.
- Production HTTPS homepage loads successfully.

---

# Notes / Known Issues

### Release environment file

The release environment file must be initialised with all expected keys before
running the release scripts.

Release scripts use awk to update values by matching existing keys and replacing
their lines. They do not create a key if it is missing. If the file is empty,
there are no lines for awk to match, so the resulting file will also be empty.

Keep all required keys present, even when their values are initially blank.

### Wait for cloud-init

A newly-created VM may accept SSH connections before provisioning has completed.

Always check:

```bash
journalctl -eu cloud-final
```

before diagnosing missing packages, groups or host configuration.

### Container architecture

Development occurs on Apple Silicon while production uses x86-64.

Production images must therefore explicitly be built for `linux/amd64`. Verify
the architecture before deployment rather than diagnosing an architecture
problem on the server.

### Configuration errors

The first production deployment exposed configuration issues that required
correcting the release configuration and redeploying.

When deployment behaves unexpectedly, verify the configuration and environment
passed to `deploy.sh` before changing application or infrastructure code.

Keep deployment variables scoped to the deployment command to avoid
contamination from existing shell environment variables.

### DNS

A healthy deployment may be complete before the public hostname starts
resolving correctly.

Treat DNS propagation separately from service health. Verify the stack through
Docker/service logs first, then wait for DNS rather than repeatedly redeploying
a healthy stack.

### Logs

`docker service logs <service-name>` is the primary tool for inspecting Swarm
service logs. Redirecting these logs to a file did not behave as expected
during the initial deployment; investigate separately if persistent log capture
is required.

---

# Timing

First clean-room production deployment:

```text
Infrastructure start:       14:00
Initial deployment healthy: 16:00
Break:                      excluded
Config debugging/redeploy:  18:40–20:00
Public homepage:            ~21:00
```

Approximate active deployment time:

**~3 hours 20 minutes**

For planning purposes, budget:

**3–4 hours from an empty cloud account to a verified production deployment**,
including checks and reasonable troubleshooting.

DNS propagation may add additional elapsed time without requiring active work.

Normal incremental releases should be considerably faster because
infrastructure provisioning, PostgreSQL provisioning and Swarm initialisation
are not repeated.
