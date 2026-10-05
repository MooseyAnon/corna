#!/usr/bin/env bash

# =============================================================================
# Corna Swarm Deployment Script
# =============================================================================
#
# This script deploys an already-built and already-published Corna release to
# the production Docker Swarm stack.
#
# Deployment is intentionally the final stage of the release lifecycle:
#
#   build.sh
#       Builds, tests, and publishes release images.
#
#   secrets.sh
#       Creates or rotates Docker Swarm secret generations.
#
#   deploy.sh
#       Applies the selected release and secret state to the Swarm cluster.
#
# This script does not build images, push images, create secrets, initialise
# Swarm, or configure the production host.
#
#
# -----------------------------------------------------------------------------
# Usage
# -----------------------------------------------------------------------------
#
#   ./infra/deploy.sh
#
# The deployment environment must be loaded first:
#
#   source .env-deployment
#
#
# -----------------------------------------------------------------------------
# Environment
# -----------------------------------------------------------------------------
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
# Registry authentication is expected to have already been configured on the
# Swarm manager.
#
# The deployment uses:
#
#   docker stack deploy --with-registry-auth
#
# so the manager can pass its registry credentials to Swarm workers when
# pulling private images.
#
#
# -----------------------------------------------------------------------------
# Release state
# -----------------------------------------------------------------------------
#
# Deployment state is stored in:
#
#   infra/release.env
#
# Relevant values are:
#
#   BUILT_VERSION
#   BUILT_COMMIT
#
#   PUSHED_VERSION
#   PUSHED_COMMIT
#
#   DEPLOYED_VERSION
#   DEPLOYED_COMMIT
#
#   TLS_CERT_SECRET
#   TLS_KEY_SECRET
#   VAULT_PASSWORD_SECRET
#
# Before deployment, the script verifies that the current Git release matches
# the successfully built and published release.
#
# The expected invariant is:
#
#   current Git HEAD
#       ==
#   exact Git release tag
#       ==
#   BUILT_VERSION / BUILT_COMMIT
#       ==
#   PUSHED_VERSION / PUSHED_COMMIT
#
# This ensures that deploy.sh cannot accidentally deploy:
#
#   - an untagged commit
#   - an unbuilt release
#   - a release that failed testing
#   - a locally built release that was never pushed
#   - images from a different Git commit
#
# DEPLOYED_VERSION and DEPLOYED_COMMIT are only updated after the rollout has
# completed successfully.
#
#
# -----------------------------------------------------------------------------
# Stack definition
# -----------------------------------------------------------------------------
#
# The Swarm stack is defined locally in:
#
#   infra/swarm.yml
#
# The stack file is not copied onto the production server.
#
# Instead it is streamed over SSH directly into:
#
#   docker stack deploy --compose-file -
#
# The flow is:
#
#   local infra/swarm.yml
#       ->
#   SSH stdin
#       ->
#   docker stack deploy
#       ->
#   Swarm desired state
#
# There is therefore no persistent swarm.yml file on the remote host which can
# drift independently from the repository.
#
# The repository remains the source of truth for the stack definition.
#
#
# -----------------------------------------------------------------------------
# Stack interpolation
# -----------------------------------------------------------------------------
#
# swarm.yml uses normal environment-variable interpolation rather than a
# templating system.
#
# deploy.sh supplies the release and secret values required by the stack.
#
# These include:
#
#   CORNA_VERSION
#   TLS_CERT_SECRET
#   TLS_KEY_SECRET
#   VAULT_PASSWORD_SECRET
#
# For example:
#
#   services:
#     corna:
#       image: ${REGISTRY}/corna:${CORNA_VERSION}
#
#   secrets:
#     tls_cert:
#       external: true
#       name: ${TLS_CERT_SECRET}
#
# Secret names may therefore change between deployments while the logical
# secret paths exposed inside containers remain stable.
#
#
# -----------------------------------------------------------------------------
# Remote host requirements
# -----------------------------------------------------------------------------
#
# Host provisioning is intentionally outside this script.
#
# Before deploy.sh is used, the production server is expected to have already
# been:
#
#   - provisioned by Terraform
#   - configured for SSH access
#   - configured with Docker
#   - initialised as a Docker Swarm manager
#   - authenticated to the private container registry
#
# Swarm initialisation and node joining are manual infrastructure operations,
# not part of routine application deployment.
#
#
# -----------------------------------------------------------------------------
# Deployment process
# -----------------------------------------------------------------------------
#
# A deployment performs the following steps:
#
#   1. Resolve the exact Git release tag and commit for the current HEAD.
#
#   2. Load infra/release.env.
#
#   3. Validate the local deployment environment.
#
#   4. Verify that the current release exactly matches the recorded successful
#      build and push state.
#
#   5. Verify that all required secret aliases are present.
#
#   6. Verify SSH access to the target host and confirm that it is an active
#      Docker Swarm manager.
#
#   7. Stream infra/swarm.yml over SSH into docker stack deploy.
#
#   8. Wait for the Swarm rollout to finish.
#
#   9. Display the resulting stack/service status.
#
#  10. Record DEPLOYED_VERSION and DEPLOYED_COMMIT in infra/release.env.
#
#
# -----------------------------------------------------------------------------
# Rollout verification
# -----------------------------------------------------------------------------
#
# A successful return code from:
#
#   docker stack deploy
#
# only means that Swarm accepted the new desired state.
#
# It does not mean that the rollout has finished successfully.
#
# deploy.sh therefore inspects each stack service's Swarm UpdateStatus and waits
# until the deployment has converged.
#
# Update states are interpreted as:
#
#   no UpdateStatus
#       The service was unchanged by this deployment. No action is required.
#
#   updating
#       The rollout is still in progress.
#
#   completed
#       The service update completed successfully.
#
#   paused
#   rollback_started
#   rollback_paused
#       The attempted deployment failed.
#
#   rollback_completed
#       Swarm recovered the service by rolling back, but the requested release
#       was not successfully deployed. The deployment is therefore considered
#       failed.
#
# Any unexpected update state is treated as an error.
#
# The rollout check also has a finite timeout so a deployment cannot wait
# indefinitely for a service that never converges.
#
#
# -----------------------------------------------------------------------------
# Deployment state
# -----------------------------------------------------------------------------
#
# DEPLOYED_VERSION and DEPLOYED_COMMIT describe the last release that this
# script successfully observed reaching the expected Swarm state.
#
# They are only updated after:
#
#   docker stack deploy
#       ->
#   rollout verification
#       ->
#   successful completion
#
# A failed deployment therefore leaves the previous DEPLOYED_* state intact.
#
# This distinguishes:
#
#   requested deployment
#
# from:
#
#   successfully completed deployment
#
#
# -----------------------------------------------------------------------------
# Secrets
# -----------------------------------------------------------------------------
#
# deploy.sh does not create or modify secret plaintext.
#
# It only reads the selected Swarm secret names from infra/release.env and
# passes those names into the stack definition.
#
# Secret rotation is handled separately by:
#
#   ./infra/secrets.sh
#
# A newly-created secret generation is unused until deploy.sh updates the Swarm
# service definition to reference it.
#
# The normal rotation lifecycle is:
#
#   create new secret generation
#       ->
#   update release.env alias
#       ->
#   deploy
#       ->
#   verify rollout
#       ->
#   manually remove old secret later
#
#
# -----------------------------------------------------------------------------
# Failure behaviour
# -----------------------------------------------------------------------------
#
# The script intentionally fails before deployment if:
#
#   - DEPLOY_HOST is missing
#   - swarm.yml is missing
#   - the current Git commit is not exactly release-tagged
#   - the current release does not match BUILT_*
#   - the current release does not match PUSHED_*
#   - a required secret alias is missing
#   - SSH access fails
#   - the remote host is not an active Swarm manager
#
# It fails during deployment if:
#
#   - docker stack deploy fails
#   - a service rollout pauses or rolls back
#   - a service enters an unexpected update state
#   - the rollout does not complete before the timeout
#
# In all failure cases, DEPLOYED_VERSION and DEPLOYED_COMMIT remain unchanged.
#
#
# -----------------------------------------------------------------------------
# Normal release workflow
# -----------------------------------------------------------------------------
#
# A complete production release is expected to look like:
#
#   source .env-deployment
#
#   ./infra/build.sh release
#
#   # Only when creating or rotating secrets:
#   ./infra/secrets.sh create-tls <generation>
#   ./infra/secrets.sh create-vault-password <generation>
#
#   ./infra/deploy.sh
#
# For ordinary releases where secrets have not changed:
#
#   source .env-deployment
#   ./infra/build.sh release
#   ./infra/deploy.sh
#
#
# -----------------------------------------------------------------------------
# Post-deployment verification
# -----------------------------------------------------------------------------
#
# Swarm convergence verifies that the orchestrator successfully rolled out the
# requested service definitions.
#
# It does not prove that Corna is functionally healthy from a user's point of
# view. This is the responsibility of application monitoring to verify.
#
# =============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RELEASE_FILE="${PROJECT_ROOT}/infra/release.env"
SWARM_FILE="${PROJECT_ROOT}/infra/swarm.yml"

STACK_NAME="corna"


# -----------------------------------------------------------------------------
# Deploy
# -----------------------------------------------------------------------------

get_release_tag() {
    local tag

    if ! tag="$(git -C "${PROJECT_ROOT}" describe --tags --exact-match HEAD 2>/dev/null)"; then
        echo "ERROR: HEAD does not have an exact git tag." >&2
        exit 1
    fi

    if [[ ! "${tag}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-rc[0-9]+)?$ ]]; then
        echo "ERROR: Invalid release tag: ${tag}" >&2
        echo "Expected format: v<major>.<minor>.<patch>" >&2
        exit 1
    fi

    TAG="${tag}"
}


get_release_commit() {
    COMMIT="$(git -C "${PROJECT_ROOT}" rev-parse HEAD)"
}


load_release_state() {
    if [[ ! -f "${RELEASE_FILE}" ]]; then
        echo "ERROR: Release file not found: ${RELEASE_FILE}" >&2
        exit 1
    fi

    # release.env is a trusted, version-controlled file in this repository.
    source "${RELEASE_FILE}"
}


validate_environment() {
    if [[ -z "${DEPLOY_HOST:-}" ]]; then
        echo "ERROR: DEPLOY_HOST is not set." >&2
        exit 1
    fi

    if [[ ! -f "${SWARM_FILE}" ]]; then
        echo "ERROR: Swarm file not found: ${SWARM_FILE}" >&2
        exit 1
    fi
}


validate_release() {
    get_release_tag
    get_release_commit
    load_release_state

    if [[ "${BUILT_VERSION:-}" != "${TAG}" \
        || "${BUILT_COMMIT:-}" != "${COMMIT}" ]]; then
        echo "ERROR: Current release has not been built." >&2
        exit 1
    fi

    if [[ "${PUSHED_VERSION:-}" != "${TAG}" \
        || "${PUSHED_COMMIT:-}" != "${COMMIT}" ]]; then
        echo "ERROR: Current release has not been pushed." >&2
        exit 1
    fi

    if [[ "${DEPLOYED_VERSION:-}" == "${TAG}" \
        && "${DEPLOYED_COMMIT:-}" == "${COMMIT}" ]]; then
        echo "ERROR: ${TAG} is already recorded as deployed." >&2
        exit 1
    fi
}


validate_secrets() {
    local secrets=(
        "${TLS_CERT_SECRET:-}"
        "${TLS_KEY_SECRET:-}"
        "${VAULT_PASSWORD_SECRET:-}"
    )

    local secret

    for secret in "${secrets[@]}"; do
        if [[ -z "${secret}" ]]; then
            echo "ERROR: Required secret alias is missing from ${RELEASE_FILE}." >&2
            exit 1
        fi
    done
}


validate_remote() {
    echo "Checking Swarm manager..."

    ssh "${DEPLOY_HOST}" \
        'docker info --format "{{.Swarm.LocalNodeState}} {{.Swarm.ControlAvailable}}"'
}


deploy_stack() {
    echo "Deploying ${TAG}..."

    ssh "${DEPLOY_HOST}" \
        "CONFIG_FILE_PATH='${CONFIG_FILE_PATH}' \
         CORNA_INVITE_APPROVAL_DIR='${CORNA_INVITE_APPROVAL_DIR}' \
         CORNA_RUNTIME_ASSET_DIR='${CORNA_RUNTIME_ASSET_DIR}' \
         DB_ADDRESS='${DB_ADDRESS}' \
         CORNA_VERSION='${TAG}' \
         REGISTRY='${REGISTRY}' \
         TAG='${TAG}' \
         TLS_CERT_SECRET='${TLS_CERT_SECRET}' \
         TLS_KEY_SECRET='${TLS_KEY_SECRET}' \
         VAULT_PASSWORD_SECRET='${VAULT_PASSWORD_SECRET}' \
         docker stack deploy \
            --with-registry-auth \
            --compose-file - \
            '${STACK_NAME}'" \
        < "${SWARM_FILE}"
}


wait_for_deployment() {
    local timeout=120
    local interval=5
    local elapsed=0

    echo "Waiting for deployment..."

    while (( elapsed < timeout )); do
        local services
        local pending=false

        services="$(
            ssh "${DEPLOY_HOST}" \
                "docker stack services '${STACK_NAME}' \
                    --format '{{.Name}}'"
        )"

        local service

        while IFS= read -r service; do
            local status

            status="$(
                ssh "${DEPLOY_HOST}" \
                    "docker service inspect \
                        --format '{{if .UpdateStatus}}{{.UpdateStatus.State}}{{end}}' \
                        '${service}'"
            )"

            case "${status}" in
                "")
                    # No update occurred for this service.
                    ;;

                completed)
                    ;;

                updating)
                    pending=true
                    ;;

                paused|rollback_started|rollback_paused)
                    echo "ERROR: Deployment failed for ${service}: ${status}" >&2
                    return 1
                    ;;

                rollback_completed)
                    echo "ERROR: Deployment rolled back for ${service}." >&2
                    return 1
                    ;;

                *)
                    echo "ERROR: Unexpected update state for ${service}: ${status}" >&2
                    return 1
                    ;;
            esac
        done <<< "${services}"

        if [[ "${pending}" == false ]]; then
            echo "Deployment completed."
            return 0
        fi

        sleep "${interval}"
        ((elapsed += interval))
    done

    echo "ERROR: Deployment did not complete within ${timeout}s." >&2
    return 1
}


show_status() {
    echo
    echo "Deployment status:"

    ssh "${DEPLOY_HOST}" \
        "docker stack services '${STACK_NAME}'"
}


record_deployment() {
    local tmp_file

    tmp_file="$(mktemp)"

    awk \
        -v version="${TAG}" \
        -v commit="${COMMIT}" \
        '
        /^DEPLOYED_VERSION=/ {
            print "DEPLOYED_VERSION=\"" version "\""
            next
        }
        /^DEPLOYED_COMMIT=/ {
            print "DEPLOYED_COMMIT=\"" commit "\""
            next
        }
        { print }
        ' \
        "${RELEASE_FILE}" > "${tmp_file}"

    mv "${tmp_file}" "${RELEASE_FILE}"
}


deploy() {
    validate_environment
    validate_release
    validate_secrets
    validate_remote

    deploy_stack
    wait_for_deployment
    show_status

    record_deployment

    echo
    echo "Successfully deployed ${TAG} (${COMMIT:0:7})"
}


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

deploy
