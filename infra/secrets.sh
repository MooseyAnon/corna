#!/usr/bin/env bash

# =============================================================================
# Corna Swarm Secret Management Script
# =============================================================================
#
# This script creates and rotates Docker Swarm secrets used by Corna.
#
# Secret creation is intentionally kept separate from application deployment:
#
#   - build.sh creates and publishes release artifacts
#   - secrets.sh creates or rotates secret generations
#   - deploy.sh updates the Swarm stack to reference the selected secrets
#
# Creating a new secret does not automatically update any running service.
# A deployment must occur before Swarm tasks begin using the new generation.
#
#
# -----------------------------------------------------------------------------
# Usage
# -----------------------------------------------------------------------------
#
#   ./infra/secrets.sh create-tls <generation>
#   ./infra/secrets.sh create-vault-password <generation>
#
# Examples:
#
#   ./infra/secrets.sh create-tls 2026_12
#   ./infra/secrets.sh create-vault-password v2
#
# Secret generations are supplied explicitly. The script does not automatically
# increment or infer them.
#
#
# -----------------------------------------------------------------------------
# Environment
# -----------------------------------------------------------------------------
#
# The deployment environment must be loaded before running this script.
#
# For example:
#
#   source .env-deployment
#
# The script expects:
#
#   DEPLOY_HOST
#       SSH host or SSH config alias for the Swarm manager.
#
#       Example:
#
#           cornaServer
#
#   ANSIBLE_VAULT_PASSWORD_FILE
#       Local path to the Ansible Vault password file used to decrypt the Corna
#       vault.
#
# The local Python environment is also expected to have already been prepared
# by uv, with the required tools available under:
#
#   .venv/bin/
#
# In particular:
#
#   .venv/bin/ansible-vault
#   .venv/bin/python
#
#
# -----------------------------------------------------------------------------
# Secret storage model
# -----------------------------------------------------------------------------
#
# Docker Swarm secrets are immutable.
#
# A secret cannot be modified in place. Rotation therefore creates a new
# generation with a new name, for example:
#
#   corna_tls_cert_2026_09
#   corna_tls_cert_2026_12
#
# The currently selected generation is stored in:
#
#   infra/release.env
#
# Relevant aliases are:
#
#   TLS_CERT_SECRET
#   TLS_KEY_SECRET
#   VAULT_PASSWORD_SECRET
#
# These aliases are consumed by deploy.sh and interpolated into swarm.yml.
#
# For example:
#
#   TLS_CERT_SECRET="corna_tls_cert_2026_12"
#
# The Swarm stack can then expose that external secret to the container using a
# stable logical name such as:
#
#   /run/secrets/tls_cert
#
# This allows the physical Swarm secret generation to change without changing
# paths expected by the application or nginx.
#
#
# -----------------------------------------------------------------------------
# Plaintext handling
# -----------------------------------------------------------------------------
#
# Secret plaintext must never be copied onto the remote host filesystem.
#
# The required property is:
#
#   local secret source
#       ->
#   stdout
#       ->
#   SSH stdin
#       ->
#   docker secret create <name> -
#
# Secret contents may travel through local process pipes and SSH, but no
# temporary plaintext secret file is created on the deployment server.
#
#
# -----------------------------------------------------------------------------
# TLS secret creation
# -----------------------------------------------------------------------------
#
# TLS certificate material is stored inside the Corna Ansible Vault.
#
# The application-level vault helper is deliberately not used here because it
# depends on Corna configuration. Deployment tooling should not need to create
# or load application config merely to retrieve deployment secrets.
#
# Instead, the script decrypts the vault directly:
#
#   ansible-vault view
#       ->
#   decrypted YAML on stdout
#       ->
#   small Python/YAML selector
#       ->
#   selected value on stdout
#
# The TLS command:
#
#   ./infra/secrets.sh create-tls <generation>
#
# creates two Swarm secrets:
#
#   corna_tls_cert_<generation>
#   corna_tls_key_<generation>
#
# The certificate and private key are read independently from the vault and
# streamed directly into:
#
#   docker secret create
#
# The corresponding TLS aliases in infra/release.env are only updated after
# both Swarm secrets have been created successfully.
#
# If certificate creation succeeds but key creation fails:
#
#   - release.env remains unchanged
#   - the successfully-created certificate secret remains in Swarm unused
#   - no attempt is made to automatically delete or roll back that secret
#
# This is deliberate. Leaving an unused immutable secret is safer than adding
# automatic destructive cleanup to the failure path.
#
#
# -----------------------------------------------------------------------------
# Vault password secret creation
# -----------------------------------------------------------------------------
#
# The vault password command:
#
#   ./infra/secrets.sh create-vault-password <generation>
#
# reads the existing local:
#
#   ANSIBLE_VAULT_PASSWORD_FILE
#
# and streams it directly to Swarm.
#
# It creates:
#
#   corna_vault_password_<generation>
#
# Only after successful creation is:
#
#   VAULT_PASSWORD_SECRET
#
# updated in infra/release.env.
#
#
# -----------------------------------------------------------------------------
# release.env
# -----------------------------------------------------------------------------
#
# infra/release.env contains the currently selected secret generations.
#
# secrets.sh mutates only the relevant secret aliases:
#
#   TLS_CERT_SECRET
#   TLS_KEY_SECRET
#   VAULT_PASSWORD_SECRET
#
# It does not modify build, push, or deployment state.
#
# Secret aliases represent the generations that the next deployment should
# reference. Updating an alias alone does not alter a running Swarm service.
#
#
# -----------------------------------------------------------------------------
# Rotation process
# -----------------------------------------------------------------------------
#
# A normal secret rotation is:
#
#   1. Create a new secret generation:
#
#          ./infra/secrets.sh create-tls 2026_12
#
#   2. secrets.sh updates release.env to reference the new generation.
#
#   3. Run deploy.sh.
#
#   4. Swarm performs a rolling update and new tasks receive the new secret.
#
#   5. Verify the deployment.
#
#   6. Remove the previous Swarm secret manually when it is no longer needed.
#
# Old secrets are never deleted automatically by this script.
#
#
# -----------------------------------------------------------------------------
# Secret naming
# -----------------------------------------------------------------------------
#
# Secret generations have a lifecycle independent from Corna application
# versions.
#
# Application releases may happen frequently, while TLS certificates and other
# credentials rotate on their own schedules.
#
# Secret names therefore do not use the current Git release tag.
#
# Suitable examples include:
#
#   corna_tls_cert_2026_12
#   corna_tls_key_2026_12
#   corna_vault_password_v2
#
# Generations may contain:
#
#   letters
#   numbers
#   dots
#   underscores
#   hyphens
#
#
# -----------------------------------------------------------------------------
# Failure and safety behaviour
# -----------------------------------------------------------------------------
#
# The script intentionally does not:
#
#   - overwrite existing Swarm secrets
#   - delete old secret generations
#   - deploy the application
#   - rebuild application images
#   - push application images
#   - copy plaintext secret files to the remote host
#
# If a requested secret name already exists, Docker Swarm will reject the
# creation rather than silently replacing it.
#
# This makes secret rotation an explicit and auditable operation.
#
#
# -----------------------------------------------------------------------------
# Normal operational workflow
# -----------------------------------------------------------------------------
#
# Secret creation is normally required only when initially provisioning Corna
# or when rotating credentials.
#
# Typical initial setup:
#
#   source .env-deployment
#
#   ./infra/secrets.sh create-tls 2026_09
#   ./infra/secrets.sh create-vault-password v1
#
# Then deploy the release using:
#
#   ./infra/deploy.sh
#
# For ordinary application releases where no secret has changed, secrets.sh
# does not need to be run.
#
# =============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RELEASE_FILE="${PROJECT_ROOT}/infra/release.env"
ANSIBLE_VAULT_PATH="${PROJECT_ROOT}/corna/utils/vault"

VENV_BIN="${PROJECT_ROOT}/.venv/bin"


# -----------------------------------------------------------------------------
# Secrets
# -----------------------------------------------------------------------------

usage() {
    cat <<'EOF'
Usage:
  ./infra/secrets.sh create-tls <generation>
  ./infra/secrets.sh create-vault-password <generation>

Examples:
  ./infra/secrets.sh create-tls 2026_12
  ./infra/secrets.sh create-vault-password v2
EOF
}


validate_environment() {
    if [[ -z "${DEPLOY_HOST:-}" ]]; then
        echo "ERROR: DEPLOY_HOST is not set." >&2
        exit 1
    fi

    if [[ -z "${ANSIBLE_VAULT_PASSWORD_FILE:-}" ]]; then
        echo "ERROR: ANSIBLE_VAULT_PASSWORD_FILE is not set." >&2
        exit 1
    fi

    if [[ ! -f "${ANSIBLE_VAULT_PASSWORD_FILE}" ]]; then
        echo "ERROR: Vault password file not found: ${ANSIBLE_VAULT_PASSWORD_FILE}" >&2
        exit 1
    fi

    if [[ ! -f "${ANSIBLE_VAULT_PATH}" ]]; then
        echo "ERROR: Vault file not found: ${ANSIBLE_VAULT_PATH}" >&2
        exit 1
    fi

    if [[ ! -x "${VENV_BIN}/ansible-vault" ]]; then
        echo "ERROR: ansible-vault not found in ${VENV_BIN}" >&2
        exit 1
    fi

    if [[ ! -x "${VENV_BIN}/python" ]]; then
        echo "ERROR: Python not found in ${VENV_BIN}" >&2
        exit 1
    fi

    if [[ ! -f "${RELEASE_FILE}" ]]; then
        echo "ERROR: Release file not found: ${RELEASE_FILE}" >&2
        exit 1
    fi
}


load_release_state() {
    # release.env is a trusted, version-controlled file in this repository.
    source "${RELEASE_FILE}"
}


validate_generation() {
    local generation="$1"

    if [[ -z "${generation}" ]]; then
        echo "ERROR: Secret generation is required." >&2
        usage
        exit 1
    fi

    if [[ ! "${generation}" =~ ^[A-Za-z0-9._-]+$ ]]; then
        echo "ERROR: Invalid secret generation: ${generation}" >&2
        exit 1
    fi
}


vault_item() {
    local key="$1"

    "${VENV_BIN}/ansible-vault" view \
        --vault-password-file "${ANSIBLE_VAULT_PASSWORD_FILE}" \
        "${ANSIBLE_VAULT_PATH}" |
        "${VENV_BIN}/python" -c "
import sys
import yaml

data = yaml.safe_load(sys.stdin)

for key in '${key}'.split('.'):
    data = data[key]

print(data)
"
}


create_remote_secret() {
    local name="$1"

    echo "Creating Swarm secret: ${name}"

    ssh "${DEPLOY_HOST}" \
        "docker secret create '${name}' -"
}


update_release_value() {
    local key="$1"
    local value="$2"
    local tmp_file

    tmp_file="$(mktemp)"

    awk \
        -v key="${key}" \
        -v value="${value}" \
        '
        $0 ~ "^" key "=" {
            print key "=\"" value "\""
            next
        }
        { print }
        ' \
        "${RELEASE_FILE}" > "${tmp_file}"

    mv "${tmp_file}" "${RELEASE_FILE}"
}


update_tls_release_values() {
    local cert_name="$1"
    local key_name="$2"
    local tmp_file

    tmp_file="$(mktemp)"

    awk \
        -v cert_name="${cert_name}" \
        -v key_name="${key_name}" \
        '
        /^TLS_CERT_SECRET=/ {
            print "TLS_CERT_SECRET=\"" cert_name "\""
            next
        }
        /^TLS_KEY_SECRET=/ {
            print "TLS_KEY_SECRET=\"" key_name "\""
            next
        }
        { print }
        ' \
        "${RELEASE_FILE}" > "${tmp_file}"

    mv "${tmp_file}" "${RELEASE_FILE}"
}


create_tls() {
    local generation="$1"

    validate_generation "${generation}"

    local cert_name="corna_tls_cert_${generation}"
    local key_name="corna_tls_key_${generation}"

    echo "Creating TLS secrets for generation ${generation}..."

    vault_item "vault.keys.ssl-certs.fullchain" |
        create_remote_secret "${cert_name}"

    vault_item "vault.keys.ssl-certs.private" |
        create_remote_secret "${key_name}"

    update_tls_release_values \
        "${cert_name}" \
        "${key_name}"

    echo "TLS secrets created:"
    echo "  ${cert_name}"
    echo "  ${key_name}"
}


create_vault_password() {
    local generation="$1"

    validate_generation "${generation}"

    local secret_name="corna_vault_password_${generation}"

    echo "Creating vault password secret for generation ${generation}..."

    cat "${ANSIBLE_VAULT_PASSWORD_FILE}" |
        create_remote_secret "${secret_name}"

    update_release_value \
        "VAULT_PASSWORD_SECRET" \
        "${secret_name}"

    echo "Vault password secret created:"
    echo "  ${secret_name}"
}


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
    validate_environment
    load_release_state

    case "${1:-}" in
        create-tls)
            create_tls "${2:-}"
            ;;

        create-vault-password)
            create_vault_password "${2:-}"
            ;;

        *)
            usage
            exit 1
            ;;
    esac
}


main "$@"
