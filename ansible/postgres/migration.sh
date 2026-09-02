#!/usr/bin/env bash

# PostgreSQL migrations
#
# Runs Corna's Alembic database migrations against either a local PostgreSQL
# instance or a remote managed PostgreSQL instance.
#
# The migration logic itself is identical in both environments. This script is
# responsible only for selecting the correct database endpoint, establishing an
# SSH tunnel when required, exporting the configuration expected by Corna, and
# invoking Alembic from the project's virtual environment.
#
# Usage:
#
#     ./migration.sh local
#     ./migration.sh remote
#
#
# LOCAL
# -----
#
# Local migrations connect directly to the PostgreSQL instance running on the
# host machine:
#
#     migration.sh
#         -> localhost:5432
#         -> Corna configuration
#         -> database.migration_url
#         -> Alembic
#
# Unlike provisioning, migrations do not use the PostgreSQL bootstrap account.
# Corna's configuration builds database.url using the dedicated
# migration/admin database role and its password from the Ansible vault.
#
#
# REMOTE
# ------
#
# The managed PostgreSQL instance is not accessed directly from the host machine.
# The script opens an SSH tunnel through SSH_HOST:
#
#     localhost:55432
#         -> SSH_HOST
#         -> REMOTE_DB_HOST:REMOTE_DB_PORT
#
# The Corna configuration is then given:
#
#     DB_ADDRESS=localhost
#     DB_PORT=55432
#
# so database.url resolves to the remote managed database through the
# local end of the SSH tunnel.
#
# The script waits for PostgreSQL to become reachable through the tunnel before
# invoking Alembic. The SSH process is tracked and cleaned up automatically when
# the migration completes, fails, or the script receives INT/TERM.
#
#
# COMMON CONFIGURATION
# --------------------
#
# .env-psql contains the values required in both local and remote modes:
#
#     DB_NAME
#     CONFIG_FILE_PATH
#     ANSIBLE_VAULT_PATH
#     ANSIBLE_VAULT_PASSWORD
#     ALEMBIC_CONFIG_PATH
#     PROJECT_DIR
#
# CONFIG_FILE_PATH points to the Corna YAML configuration used specifically for
# migrations.
#
# ANSIBLE_VAULT_PATH and ANSIBLE_VAULT_PASSWORD allow Corna's configuration
# loader to retrieve the database credentials required to build
# database.url.
#
# ALEMBIC_CONFIG_PATH points to alembic.ini. Alembic's script_location should
# be relative to the config file using %(here)s so migrations are independent
# of the shell's current working directory.
#
# PROJECT_DIR identifies the Corna Python project root. Alembic is invoked directly
# from:
#
#     ${PROJECT_DIR}/.venv/bin/alembic
#
# rather than through `uv run`, so migration execution does not depend on uv
# discovering the correct project from the current working directory.
#
#
# REMOTE CONFIGURATION
# --------------------
#
# Remote migrations additionally require .env-remote:
#
#     SSH_HOST
#     REMOTE_DB_HOST
#     REMOTE_DB_PORT
#
# SSH_HOST must be able to reach REMOTE_DB_HOST:REMOTE_DB_PORT.
#
# Remote migrations deliberately do not require the managed database bootstrap
# credentials. Provisioning creates the Corna migration/admin role once, and all
# subsequent schema migrations authenticate using database.url from the
# normal Corna config and vault.
#
#
# DATABASE CONFIGURATION
# ----------------------
#
# The script exports:
#
#     DB_ADDRESS
#     DB_PORT
#     DB_NAME
#     CONFIG_FILE_PATH
#     ANSIBLE_VAULT_PATH
#     ANSIBLE_VAULT_PASSWORD
#
# Corna's config loader consumes these values and constructs:
#
#     get_config().database.url
#
# ALEMBIC
# -------
#
# The script ultimately runs:
#
#     ${PROJECT_DIR}/.venv/bin/alembic \
#         -c "${ALEMBIC_CONFIG_PATH}" \
#         upgrade head
#
# Alembic therefore applies every outstanding migration up to the current head.
#
# The exact same command and migration files are used for local and remote
# databases. Only DB_ADDRESS and DB_PORT differ between the two states.
#
#
# This script requires:
#
#   - the Corna project virtual environment;
#   - Alembic installed in that virtual environment;
#   - the Corna migration config;
#   - access to the configured Ansible vault;
#   - .env-psql;
#   - pg_isready (remote mode);
#   - ssh (remote mode);
#   - .env-remote (remote mode only).
#
# Secrets and environment files must not be committed to source control.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env-psql"
REMOTE_ENV_FILE="${SCRIPT_DIR}/.remote-env"

LOCAL_DB_ADDRESS="localhost"
LOCAL_DB_PORT=5432
LOCAL_TUNNEL_PORT=55432

SSH_PID=""


validate_mode() {
    local mode="${1:-}"

    case "${mode}" in
        local|remote)
            ;;
        *)
            echo "Usage: $0 <local|remote>" >&2
            exit 1
            ;;
    esac
}


validate_common_env() {
    local required_vars=(
        DB_NAME
        CONFIG_FILE_PATH
        ANSIBLE_VAULT_PATH
        ANSIBLE_VAULT_PASSWORD
        ALEMBIC_CONFIG_PATH
        PROJECT_DIR
    )

    if [[ ! -f "${ENV_FILE}" ]]; then
        echo "Missing PostgreSQL environment file: ${ENV_FILE}" >&2
        exit 1
    fi

    # shellcheck disable=SC1090
    source "${ENV_FILE}"

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            echo "Missing required variable in ${ENV_FILE}: ${var}" >&2
            exit 1
        fi
    done

    if [[ ! -f "${CONFIG_FILE_PATH}" ]]; then
        echo "Missing application config file: ${CONFIG_FILE_PATH}" >&2
        exit 1
    fi

    if [[ ! -f "${ALEMBIC_CONFIG_PATH}" ]]; then
        echo "Missing Alembic config file: ${ALEMBIC_CONFIG_PATH}" >&2
        exit 1
    fi

    if [[ ! -x "${PROJECT_DIR}/.venv/bin/alembic" ]]; then
        echo "Missing Alembic executable: ${PROJECT_DIR}/.venv/bin/alembic" >&2
        exit 1
    fi
}


validate_remote_env() {
    local required_vars=(
        SSH_HOST
        REMOTE_DB_HOST
        REMOTE_DB_PORT
    )

    if [[ ! -f "${REMOTE_ENV_FILE}" ]]; then
        echo "Missing remote environment file: ${REMOTE_ENV_FILE}" >&2
        exit 1
    fi

    # shellcheck disable=SC1090
    source "${REMOTE_ENV_FILE}"

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            echo "Missing required variable in ${REMOTE_ENV_FILE}: ${var}" >&2
            exit 1
        fi
    done
}


cleanup() {
    if [[ -n "${SSH_PID}" ]] && kill -0 "${SSH_PID}" 2>/dev/null; then
        kill "${SSH_PID}" 2>/dev/null || true
        wait "${SSH_PID}" 2>/dev/null || true
    fi
}


open_ssh_tunnel() {
    ssh \
        -o ExitOnForwardFailure=yes \
        -N \
        -L "${LOCAL_TUNNEL_PORT}:${REMOTE_DB_HOST}:${REMOTE_DB_PORT}" \
        "${SSH_HOST}" &

    SSH_PID=$!
}


wait_for_database() {
    local host="$1"
    local port="$2"
    local attempts=30

    for ((i = 1; i <= attempts; i++)); do
        if ! kill -0 "${SSH_PID}" 2>/dev/null; then
            echo "SSH tunnel exited before PostgreSQL became reachable" >&2
            exit 1
        fi

        if pg_isready \
            -h "${host}" \
            -p "${port}" \
            >/dev/null 2>&1
        then
            return 0
        fi

        sleep 1
    done

    echo "PostgreSQL did not become reachable at ${host}:${port}" >&2
    exit 1
}


run_migration() {
    local db_address="$1"
    local db_port="$2"

    export DB_ADDRESS="${db_address}"
    export DB_PORT="${db_port}"
    export DB_USER="${DB_ADMIN_USER}"
    export DB_NAME
    export CONFIG_FILE_PATH
    export ANSIBLE_VAULT_PATH
    export ANSIBLE_VAULT_PASSWORD
    # this is needed to resolve imports
    export PYTHONPATH="${PROJECT_DIR}"

    "${PROJECT_DIR}/.venv/bin/alembic" \
        -c "${ALEMBIC_CONFIG_PATH}" \
        upgrade head
}


run_local() {
    run_migration "${LOCAL_DB_ADDRESS}" "${LOCAL_DB_PORT}"
}


run_remote() {
    validate_remote_env
    open_ssh_tunnel
    wait_for_database "localhost" "${LOCAL_TUNNEL_PORT}"
    run_migration "localhost" "${LOCAL_TUNNEL_PORT}"
}


main() {
    local mode="${1:-}"

    validate_mode "${mode}"
    validate_common_env

    trap cleanup EXIT INT TERM

    case "${mode}" in
        local)
            run_local
            ;;
        remote)
            run_remote
            ;;
    esac
}


main "$@"
