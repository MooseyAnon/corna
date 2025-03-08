#!/usr/bin/env bash

set -o pipefail

help() {
    # Display Help
    echo "Interact with docker compose in order to run Corna."
    echo "This script wraps all the necessary env variables to make "
    echo "running corna simple."
    echo
    echo "Syntax: run-local-docker.sh [-h|b|c]"
    echo "options:"
    echo "-h     Print this Help."
    echo "-b     Rebuild one or all of the containers must be one of: nginx | corna | both."
    echo "-c     Run docker compose commands, must be one of: up | down | logs."
    echo "-i     Run CI, this is a flag."
    echo
}


        exit 1
    fi
}


compose() {
    local opt="${1}"
    if [[ "${opt}" = "up" ]]; then
        # run docker compose and detach container (-d).
        # Wait till all containers are healthy (--wait)
        docker compose up -d --wait
    elif [[ "${opt}" = "logs" ]]; then
        docker compose logs
    elif [[ "${opt}" = "down" ]]; then
        docker compose down
    elif [[ "${opt}" = "status" ]]; then
        docker compose ps
    fi
}


build() {
    local opt="${1}"

    if [[ "${opt}" = "both" ]]; then
        docker compose up -d --build
    else
        echo "Building ${opt} container..."
        # this command rebuilds the container (or pulls it)
        # and then replaces the current running container once
        # the build is complete.
        # more info: https://stackoverflow.com/q/42529211
        docker compose up -d --no-deps --build "${opt}"
    fi
}


my_ip() {
    # we want to dynampically get our local host IP address to
    # connect to postgres from inside the container. The reason
    # for this is because "localhost" inside the container and
    # on the host are different, so trying to conntect to localhost
    # from our service wont work.
    # taken from here: https://stackoverflow.com/q/13322485
    INTERFACE=${1:-"en0"}
    ifconfig $INTERFACE | sed -En \
        's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p'
}


run() {
    # run compose
    if [[ -n "${BUILD}" ]] && [[ -n "${COMPOSE}" ]]; then
        echo "You can not both build and run other compose commands"
        exit 1
    fi

    # if [[ -n "${RUN_CI}" ]]; then ci; fi
    if [[ -n "${BUILD}" ]]; then build "${BUILD}"; fi
    if [[ -n "${COMPOSE}" ]]; then compose "${COMPOSE}"; fi
}


cleanup() {

    for file in .env .vault-password; do
        if [ -f $file ]; then
            rm $file
        fi
    done
}

trap cleanup SIGINT

# Get the options
while getopts ":ihb:c:" option; do
   case $option in
        h) # display Help
           help
           exit
           ;;
        b) # build
            BUILD=$OPTARG
            [[ ! $BUILD =~ ^("nginx"|"corna"|"both")$ ]] && {
                echo "Error Invalid option: -b $BUILD"
                exit 1
            }
            ;;
        c) # compose
            COMPOSE=$OPTARG
            [[ ! $COMPOSE =~ ^("up"|"down"|"logs"|"status")$ ]] && {
                echo "Error Invalid option: -c $COMPOSE"
                exit 1
            }
            ;;
        i) # CI
            RUN_CI="true" ;;
        \?) # Invalid option
            echo "Error: Invalid option"
            exit;;
   esac
done


cat <<EOT>> .env
ANSIBLE_VAULT_PATH=/home/corna-user/workspace/corna/utils/vault
# this path is created by the docker secrets functionality
ANSIBLE_VAULT_PASSWORD_FILE_IN_CONTAINER=/run/secrets/vault_password
DB_ADDRESS=$(my_ip)
DB_USER=cornauser
DB_PORT=5432
DB_NAME=corna
CORNA_PORT=5001
PICTURE_DIR=$(pwd)/tmp-assets
SSL_MODE=prefer
EOT


rsync \
    --chmod=Fu=rw \
    "${ANSIBLE_VAULT_PASSWORD_FILE}" .vault-password

run
# clean up
cleanup
echo "docker compose up complete"
