#!/usr/bin/env bash

# PostgreSQL provisioning
#
# Provisions the PostgreSQL database and roles required by Corna.
#
# The same provisioning SQL is used for both local development and the remote
# managed PostgreSQL instance. This script is responsible only for establishing
# the appropriate connection to PostgreSQL and supplying provision.sql with the
# values it needs.
#
# Usage:
#
#     ./provision.sh local
#     ./provision.sh remote
#
#
# LOCAL
# -----
#
# Local provisioning connects directly to a PostgreSQL instance running on
# localhost.
#
# The bootstrap PostgreSQL role is "postgres". No host is passed to psql, so
# PostgreSQL is accessed through its Unix socket rather than TCP. This allows
# the local postgres role to authenticate using the local/peer pg_hba.conf rule
# and means no password is required for the bootstrap account.
#
#     provision.sh
#         -> local Unix socket
#         -> postgres bootstrap role
#         -> provision.sql
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
# psql then connects to localhost:55432 using the managed database's bootstrap
# account. The bootstrap password is supplied through PGPASSWORD and is not
# included in the connection URL or command-line arguments.
#
# The script waits for PostgreSQL to become reachable through the tunnel before
# running provision.sql. The SSH process is tracked and cleaned up automatically
# when provisioning completes, fails, or the script receives INT/TERM.
#
#
# COMMON CONFIGURATION
# --------------------
#
# .env-psql contains the database and role configuration shared by local and
# remote provisioning:
#
#     DB_NAME
#     DB_ADMIN_USER
#     DB_ADMIN_PASSWORD
#     DB_APP_USER
#     DB_APP_PASSWORD
#
# DB_ADMIN_USER is the migration/schema role. It owns or can modify Corna's
# schema and is intended for operations such as Alembic migrations.
#
# DB_APP_USER is the runtime application role. It can read and modify application
# data but cannot create, alter, or drop schema objects.
#
# Both role passwords are passed to provision.sql as psql variables. They are
# deliberately kept outside the version-controlled SQL file.
#
#
# REMOTE CONFIGURATION
# --------------------
#
# Remote provisioning additionally requires .env-remote:
#
#     SSH_HOST
#     REMOTE_DB_HOST
#     REMOTE_DB_PORT
#     BOOTSTRAP_DB_USER
#     BOOTSTRAP_DB_PASSWORD
#
# SSH_HOST must be able to reach REMOTE_DB_HOST:REMOTE_DB_PORT.
#
# The bootstrap database account is only used to provision the Corna database
# and roles. Normal application connections use DB_APP_USER and migrations use
# DB_ADMIN_USER.
#
#
# PROVISIONING SQL
# ----------------
#
# provision.sql is responsible for:
#
#   - creating the migration/admin role if it does not already exist;
#   - creating the application role if it does not already exist;
#   - creating the Corna database if it does not already exist;
#   - configuring database/schema permissions;
#   - granting the application role access to existing tables and sequences;
#   - configuring default privileges for tables and sequences created later by
#     the migration/admin role.
#
# Provisioning is intentionally idempotent. Existing roles and their passwords
# are not modified on subsequent runs. Password rotation is therefore a separate
# administrative operation rather than an implicit side effect of provisioning.
#
# This script requires:
#
#   - psql
#   - pg_isready (remote mode)
#   - ssh (remote mode)
#   - provision.sql
#   - .psql-env
#   - .remote-env (remote mode only)
#
# Secrets and environment files must not be committed to source control.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env-psql"
REMOTE_ENV_FILE="${SCRIPT_DIR}/.env-remote"
PROVISION_FILE="${SCRIPT_DIR}/provision.sql"

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
        DB_ADMIN_USER
        DB_ADMIN_PASSWORD
        DB_APP_USER
        DB_APP_PASSWORD
    )

    if [[ ! -f "${ENV_FILE}" ]]; then
        echo "Missing PostgreSQL environment file: ${ENV_FILE}" >&2
        exit 1
    fi

    if [[ ! -f "${PROVISION_FILE}" ]]; then
        echo "Missing PostgreSQL provisioning file: ${PROVISION_FILE}" >&2
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
}


validate_remote_env() {
    local required_vars=(
        SSH_HOST
        REMOTE_DB_HOST
        REMOTE_DB_PORT
        BOOTSTRAP_DB_USER
        BOOTSTRAP_DB_PASSWORD
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


run_psql() {
    local user="$1"
    local port="$2"
    local host="${3:-}"
    local password="${4:-}"

    local connection_args=(
        -p "${port}"
        -U "${user}"
    )

    if [[ -n "${host}" ]]; then
        connection_args+=(-h "${host}")
    fi

    # remote path
    if [[ -n "${password}" ]]; then
        PGPASSWORD="${password}" \
        psql \
            "${connection_args[@]}" \
            -v ON_ERROR_STOP=1 \
            -v db_name="${DB_NAME}" \
            -v admin_user="${DB_ADMIN_USER}" \
            -v admin_password="${DB_ADMIN_PASSWORD}" \
            -v app_user="${DB_APP_USER}" \
            -v app_password="${DB_APP_PASSWORD}" \
            -f "${PROVISION_FILE}"
        return
    fi

    # local path
    psql \
        "${connection_args[@]}" \
        -v ON_ERROR_STOP=1 \
        -v db_name="${DB_NAME}" \
        -v admin_user="${DB_ADMIN_USER}" \
        -v admin_password="${DB_ADMIN_PASSWORD}" \
        -v app_user="${DB_APP_USER}" \
        -v app_password="${DB_APP_PASSWORD}" \
        -f "${PROVISION_FILE}"
}


run_local() {
    # No host is supplied here so psql uses the local Unix socket. This allows
    # the local bootstrap "postgres" role to authenticate using the pg_hba.conf
    # local/peer rule instead of requiring a password.
    run_psql "postgres" "${LOCAL_DB_PORT}"
}


run_remote() {
    validate_remote_env

    open_ssh_tunnel
    wait_for_database "localhost" "${LOCAL_TUNNEL_PORT}"

    run_psql \
        "${BOOTSTRAP_DB_USER}" \
        "${LOCAL_TUNNEL_PORT}" \
        "localhost" \
        "${BOOTSTRAP_DB_PASSWORD}"
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
