#!/usr/bin/env bash

# Local Docker Compose runner for Corna.
#
# This script exists exclusively for local development. Production deployment
# uses Docker Swarm and has a separate build/deployment process.
#
# Local runtime state is kept under:
#
#   .tmp-compose/
#   ├── .env
#   ├── certs/
#   │   ├── cert.pem
#   │   └── key.pem
#   ├── runtime-assets/
#   └── invite-processor/
#
# The runtime directory intentionally survives `docker compose down`.
#
# In particular:
#
# - mkcert certificates are reusable development certificates and do not need
#   to be regenerated for every run.
# - runtime-assets contains locally uploaded media and should survive container
#   restarts. It can be manually deleted when resetting the development DB.
# - invite-processor contains the local approval queue and similarly survives
#   container restarts.
#
# The generated .env file is only used for Docker Compose interpolation.
# Application configuration belongs in development.yml and should not be
# duplicated here.
#
# Usage:
#
#   ./compose.sh -c up
#   ./compose.sh -c down
#   ./compose.sh -c logs
#   ./compose.sh -c status
#
#   ./compose.sh -b nginx
#   ./compose.sh -b corna
#   ./compose.sh -b invite_processor
#   ./compose.sh -b all

set -euo pipefail


PROJECT_ROOT="$(
    cd "$(dirname "${BASH_SOURCE[0]}")"
    pwd
)"

RUNTIME_DIR="${PROJECT_ROOT}/.tmp-compose"
CERT_DIR="${RUNTIME_DIR}/certs"
ASSET_DIR="${RUNTIME_DIR}/runtime-assets"
INVITE_PROCESSOR_DIR="${RUNTIME_DIR}/invite-processor"
COMPOSE_ENV="${RUNTIME_DIR}/.env"

LOCAL_DOMAIN="testingcorna.test"


help() {
    echo "Run the local Corna Docker Compose stack."
    echo
    echo "Syntax:"
    echo "  compose.sh -c <command>"
    echo "  compose.sh -b <service>"
    echo
    echo "Compose commands:"
    echo "  up"
    echo "  down"
    echo "  logs"
    echo "  status"
    echo
    echo "Build targets:"
    echo "  nginx"
    echo "  corna"
    echo "  invite_processor"
    echo "  all"
}


copy_vault_password() {
    # Copy the host vault password into the Compose runtime directory so it
    # can be included in local-only container builds.
    local destination="${RUNTIME_DIR}/.vault-password"

    if [[ -z "${ANSIBLE_VAULT_PASSWORD_FILE:-}" ]]; then
        echo "ANSIBLE_VAULT_PASSWORD_FILE is not set." >&2
        exit 1
    fi

    if [[ ! -f "${ANSIBLE_VAULT_PASSWORD_FILE}" ]]; then
        echo "Vault password file does not exist: ${ANSIBLE_VAULT_PASSWORD_FILE}" >&2
        exit 1
    fi

    cp "${ANSIBLE_VAULT_PASSWORD_FILE}" "${destination}"
    chmod 600 "${destination}"
}


delete_vault_password() {
    echo "Deleting vault password"
    # The copied password only needs to exist while Docker is building the
    # local image. Never leave the additional copy behind.
    rm -f "${RUNTIME_DIR}/.vault-password"
}


my_ip() {
    # Return the host IP used by containers to connect back to services
    # running directly on the development machine, such as PostgreSQL.
    local interface="${1:-en0}"

    ifconfig "${interface}" |
        sed -En \
            's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p'
}


ensure_runtime_dir() {
    # Keep all Compose-owned local state together rather than scattering
    # generated files throughout the repository root.
    mkdir -p \
        "${CERT_DIR}" \
        "${ASSET_DIR}" \
        "${INVITE_PROCESSOR_DIR}"
}


ensure_mkcert() {
    if ! command -v mkcert >/dev/null 2>&1; then
        echo "mkcert is required for local TLS." >&2
        echo "Install mkcert before running the Corna Compose stack." >&2
        exit 1
    fi
}


ensure_certs() {
    local cert="${CERT_DIR}/cert.pem"
    local key="${CERT_DIR}/key.pem"

    if [[ -f "${cert}" && -f "${key}" ]]; then
        return 0
    fi

    ensure_mkcert

    echo "Generating local TLS certificates for ${LOCAL_DOMAIN}..."

    # Corna derives the API hostname from the main service URL, so include
    # both the application domain and its API subdomain in the certificate.
    mkcert \
        -cert-file "${cert}" \
        -key-file "${key}" \
        "${LOCAL_DOMAIN}" \
        "api.${LOCAL_DOMAIN}"

    chmod 600 "${cert}" "${key}"
}


write_compose_env() {
    local host_ip
    host_ip="$(my_ip)"

    if [[ -z "${host_ip}" ]]; then
        echo "Unable to determine local host IP." >&2
        exit 1
    fi

    # This file is intentionally limited to values Docker Compose itself needs
    # for interpolation. Corna application configuration remains in
    # development.yml.
    cat > "${COMPOSE_ENV}" <<EOF
DB_ADDRESS=${host_ip}
CORNA_RUNTIME_ASSET_DIR=${ASSET_DIR}
CORNA_INVITE_APPROVAL_DIR=${INVITE_PROCESSOR_DIR}
CORNA_SSL_CERT_DIR=${CERT_DIR}
CONFIG_FILE_PATH=/home/corna-user/workspace/dev-conf.yml
EOF

    chmod 600 "${COMPOSE_ENV}"
}


prepare_runtime() {
    ensure_runtime_dir
    ensure_certs
    write_compose_env
}


docker_compose() {
    # Always use the generated Compose environment explicitly. This avoids
    # relying on or creating a repository-root .env file.
    docker compose \
        --env-file "${COMPOSE_ENV}" \
        "$@"
}


compose_up() {
    prepare_runtime

    docker_compose up \
        -d \
        --wait
}


compose_down() {
    # Runtime state deliberately survives `down`. Uploaded media, certificates
    # and pending invite-processor state should only disappear when the
    # developer explicitly resets the local environment.
    if [[ ! -f "${COMPOSE_ENV}" ]]; then
        prepare_runtime
    fi

    docker_compose down
}


compose_logs() {
    if [[ ! -f "${COMPOSE_ENV}" ]]; then
        prepare_runtime
    fi

    docker_compose logs
}


compose_status() {
    if [[ ! -f "${COMPOSE_ENV}" ]]; then
        prepare_runtime
    fi

    docker_compose ps
}


compose_command() {
    local command="${1}"

    case "${command}" in
        up)
            compose_up
            ;;
        down)
            compose_down
            ;;
        logs)
            compose_logs
            ;;
        status)
            compose_status
            ;;
        *)
            echo "Unknown Compose command: ${command}" >&2
            exit 1
            ;;
    esac
}


build() {
    local service="${1}"

    prepare_runtime

    make clean-macos

    copy_vault_password

    case "${service}" in
        nginx|corna|invite_processor)
            echo "Building ${service}..."

            docker_compose up \
                -d \
                --no-deps \
                --build \
                "${service}"
            ;;

        all)
            echo "Building all local services..."

            docker_compose up \
                -d \
                --build
            ;;

        *)
            echo "Unknown build target: ${service}" >&2
            exit 1
            ;;
    esac
}


run() {
    if [[ -n "${BUILD:-}" && -n "${COMPOSE_COMMAND:-}" ]]; then
        echo "Build and Compose commands cannot be used together." >&2
        exit 1
    fi

    if [[ -n "${BUILD:-}" ]]; then
        build "${BUILD}"
        return
    fi

    if [[ -n "${COMPOSE_COMMAND:-}" ]]; then
        compose_command "${COMPOSE_COMMAND}"
        return
    fi

    help
}


while getopts ":hb:c:" option; do
    case "${option}" in
        h)
            help
            exit 0
            ;;

        b)
            BUILD="${OPTARG}"

            if [[ ! "${BUILD}" =~ ^(nginx|corna|invite_processor|all)$ ]]; then
                echo "Invalid build target: ${BUILD}" >&2
                exit 1
            fi
            ;;

        c)
            COMPOSE_COMMAND="${OPTARG}"

            if [[ ! "${COMPOSE_COMMAND}" =~ ^(up|down|logs|status)$ ]]; then
                echo "Invalid Compose command: ${COMPOSE_COMMAND}" >&2
                exit 1
            fi
            ;;

        :)
            echo "Option -${OPTARG} requires an argument." >&2
            exit 1
            ;;

        \?)
            echo "Unknown option: -${OPTARG}" >&2
            exit 1
            ;;
    esac
done


# always delete vault password
trap delete_vault_password EXIT

run
