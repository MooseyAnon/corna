#!/usr/bin/env bash

# =============================================================================
# Corna Build and Release Script
# =============================================================================
#
# This script builds, validates, and publishes the Docker images that make up a
# Corna release.
#
# It deliberately separates the release lifecycle into three operations:
#
#   build
#       Build and validate the release locally.
#
#   push
#       Push an already-built release to the configured container registry.
#
#   release
#       Perform both operations in sequence: build, then push.
#
#
# -----------------------------------------------------------------------------
# Usage
# -----------------------------------------------------------------------------
#
#   ./infra/build.sh build
#   ./infra/build.sh push
#   ./infra/build.sh release
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
#   REGISTRY
#       Container registry prefix used when tagging production images.
#
#       Example:
#
#           registry.example.com/corna
#
#
# -----------------------------------------------------------------------------
# Release identity
# -----------------------------------------------------------------------------
#
# Releases are identified by the exact Git tag attached to the current commit.
#
# Valid release tags have the form:
#
#   v<major>.<minor>.<patch>
#
# For example:
#
#   v0.1.0
#
# The script also records the exact Git commit SHA associated with the tag.
#
# The current HEAD must therefore be directly tagged before a release can be
# built or pushed. Arbitrary version strings are not accepted.
#
# This gives each published image a deterministic relationship:
#
#   Git tag
#       ->
#   Git commit
#       ->
#   Docker image tag
#
# Images are never published using "latest".
#
#
# -----------------------------------------------------------------------------
# Build process
# -----------------------------------------------------------------------------
#
# The build operation performs the following steps:
#
#   1. Validate the current Git release and build state.
#
#   2. Build the development/test Corna image for the native host architecture.
#
#   3. Run the project's test suite inside that image using:
#
#          make check
#
#   4. Compile and validate the frontend TypeScript.
#
#   5. Build the production Corna image for linux/amd64.
#
#   6. Tag the same Corna image as the invite processor image.
#
#      The invite processor uses the same application image as Corna, but runs
#      with a different container command.
#
#   7. Build the production nginx image for linux/amd64.
#
#   8. Record the successful build in infra/release.env.
#
# Production images are therefore created with their final registry-qualified
# names during the build itself:
#
#   ${REGISTRY}/corna:<version>
#   ${REGISTRY}/corna-invite-processor:<version>
#   ${REGISTRY}/corna-nginx:<version>
#
# Building an image with a registry-qualified name does not publish it. The
# images remain local until the push operation is run.
#
#
# -----------------------------------------------------------------------------
# Architecture
# -----------------------------------------------------------------------------
#
# The development/test image is built for the architecture of the machine
# running this script.
#
# This allows local development machines and CI runners to execute tests
# natively.
#
# Production images are explicitly built for:
#
#   linux/amd64
#
# because that is the architecture used by the production Corna server.
#
#
# -----------------------------------------------------------------------------
# Push process
# -----------------------------------------------------------------------------
#
# The push operation does not build or retag images.
#
# It:
#
#   1. Validates that the current Git release exactly matches the release
#      recorded as successfully built.
#
#   2. Validates that all expected local production image tags exist.
#
#   3. Pushes each release image explicitly to the registry.
#
#   4. Records the successful publication in infra/release.env.
#
# The images pushed are:
#
#   ${REGISTRY}/corna:<version>
#   ${REGISTRY}/corna-invite-processor:<version>
#   ${REGISTRY}/corna-nginx:<version>
#
# A failed or partial push does not update PUSHED_VERSION or PUSHED_COMMIT.
#
# Re-running the push operation is therefore safe: already-uploaded immutable
# image layers can be reused by the registry while missing images/layers are
# retried.
#
#
# -----------------------------------------------------------------------------
# Release state
# -----------------------------------------------------------------------------
#
# Build and publication state is stored in:
#
#   infra/release.env
#
# Relevant values are:
#
#   BUILT_VERSION
#   BUILT_COMMIT
#   PUSHED_VERSION
#   PUSHED_COMMIT
#
# These values describe completed operations rather than requested operations.
#
# BUILT_* is only updated after the complete build and test process succeeds.
#
# PUSHED_* is only updated after every expected image has been successfully
# pushed.
#
# The deployment script later uses this state to ensure that only a release
# which has been successfully built and published can be deployed.
#
#
# -----------------------------------------------------------------------------
# Release invariants
# -----------------------------------------------------------------------------
#
# During a normal release:
#
#   current Git HEAD
#       ==
#   exact Git release tag
#       ==
#   BUILT_VERSION / BUILT_COMMIT
#       ==
#   PUSHED_VERSION / PUSHED_COMMIT
#
# This prevents accidental deployment of:
#
#   - untagged commits
#   - locally modified release identities
#   - images from a previous release
#   - releases which failed testing
#   - releases which were built but never published
#
#
# -----------------------------------------------------------------------------
# Normal release workflow
# -----------------------------------------------------------------------------
#
# To build without publishing:
#
#   ./infra/build.sh build
#
# To publish a previously built release:
#
#   ./infra/build.sh push
#
# For the normal complete release path:
#
#   ./infra/build.sh release
#
# This script stops at publication. Creating Swarm secrets and deploying the
# release are separate operational concerns handled by:
#
#   infra/secrets.sh
#   infra/deploy.sh
#
# =============================================================================

set -euo pipefail

# this script should be called from project root i.e. ./infra/build.sh

# -----------------------------------------------------------------------------
# Build
# -----------------------------------------------------------------------------

RELEASE_FILE="${PROJECT_ROOT}/infra/release.env"

DEV_CORNA_DOCKERFILE="${PROJECT_ROOT}/docker/dev/corna.Dockerfile"
PROD_CORNA_DOCKERFILE="${PROJECT_ROOT}/infra/docker/prod/corna.Dockerfile"
PROD_NGINX_DOCKERFILE="${PROJECT_ROOT}/infra/docker/prod/nginx.Dockerfile"


get_release_tag() {
    local tag

    if ! tag="$(git -C "${PROJECT_ROOT}" describe --tags --exact-match HEAD 2>/dev/null)"; then
        echo "ERROR: HEAD does not have an exact git tag." >&2
        exit 1
    fi

    if [[ ! "${tag}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
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


validate_build() {
    get_release_tag
    get_release_commit
    load_release_state

    if [[ "${BUILT_VERSION:-}" == "${TAG}" \
        && "${BUILT_COMMIT:-}" == "${COMMIT}" ]]; then
        echo "ERROR: ${TAG} has already been built." >&2
        exit 1
    fi

    echo "Building ${TAG} (${COMMIT:0:7})"
}


build_test_image() {
    echo "Building test image..."

    docker buildx build \
        --load \
        --file "${DEV_CORNA_DOCKERFILE}" \
        --tag "corna-test:${TAG}" \
        "${PROJECT_ROOT}"
}


run_tests() {
    echo "Running test suite..."

    docker run \
        --rm \
        "corna-test:${TAG}" \
        make check
}


run_eslint() {
    echo "Running eslint..."

    if [[ ! -d "${PROJECT_ROOT}/frontend/node_modules" ]]; then
        npm install --prefix "${PROJECT_ROOT}/frontend"
    fi

    npm run lint --prefix "${PROJECT_ROOT}/frontend"
}


compile_typescript() {
    echo "Building frontend..."

    if [[ ! -d "${PROJECT_ROOT}/frontend/node_modules" ]]; then
        npm install --prefix "${PROJECT_ROOT}/frontend"
    fi

    run_eslint
    npm run build --prefix "${PROJECT_ROOT}/frontend"
}


build_corna_image() {
    echo "Building Corna production image..."

    docker buildx build \
        --platform linux/amd64 \
        --load \
        --file "${PROD_CORNA_DOCKERFILE}" \
        --tag "${REGISTRY}/corna:${TAG}" \
        "${PROJECT_ROOT}"
}


tag_invite_processor_image() {
    echo "Tagging invite processor image..."

    docker tag \
        "${REGISTRY}/corna:${TAG}" \
        "${REGISTRY}/corna-invite-processor:${TAG}"
}


build_nginx_image() {
    echo "Building nginx production image..."

    docker buildx build \
        --platform linux/amd64 \
        --load \
        --file "${PROD_NGINX_DOCKERFILE}" \
        --tag "${REGISTRY}/corna-nginx:${TAG}" \
        "${PROJECT_ROOT}"
}


record_build() {
    local tmp_file

    tmp_file="$(mktemp)"

    # Preserve deployment/secret state while replacing the build state.
    awk \
        -v version="${TAG}" \
        -v commit="${COMMIT}" \
        '
        /^BUILT_VERSION=/ {
            print "BUILT_VERSION=\"" version "\""
            next
        }
        /^BUILT_COMMIT=/ {
            print "BUILT_COMMIT=\"" commit "\""
            next
        }
        { print }
        ' \
        "${RELEASE_FILE}" > "${tmp_file}"

    mv "${tmp_file}" "${RELEASE_FILE}"
}


build() {
    validate_build

    build_test_image
    run_tests

    compile_typescript

    build_corna_image
    tag_invite_processor_image
    build_nginx_image

    record_build

    echo "Successfully built ${TAG} (${COMMIT:0:7})"
}


# -----------------------------------------------------------------------------
# Push
# -----------------------------------------------------------------------------

validate_push() {
    get_release_tag
    get_release_commit
    load_release_state

    if [[ "${BUILT_VERSION:-}" != "${TAG}" \
        || "${BUILT_COMMIT:-}" != "${COMMIT}" ]]; then
        echo "ERROR: Current release has not been built." >&2
        echo "Current: ${TAG} (${COMMIT:0:7})" >&2
        echo "Built:   ${BUILT_VERSION:-<none>} (${BUILT_COMMIT:-<none>})" >&2
        exit 1
    fi

    if [[ "${PUSHED_VERSION:-}" == "${TAG}" \
        && "${PUSHED_COMMIT:-}" == "${COMMIT}" ]]; then
        echo "ERROR: ${TAG} has already been pushed." >&2
        exit 1
    fi
}


validate_images() {
    local images=(
        "${REGISTRY}/corna:${TAG}"
        "${REGISTRY}/corna-invite-processor:${TAG}"
        "${REGISTRY}/corna-nginx:${TAG}"
    )

    local image

    for image in "${images[@]}"; do
        if ! docker image inspect "${image}" > /dev/null 2>&1; then
            echo "ERROR: Image not found: ${image}" >&2
            exit 1
        fi
    done
}


push_images() {
    echo "Pushing images..."

    docker push "${REGISTRY}/corna:${TAG}"
    docker push "${REGISTRY}/corna-invite-processor:${TAG}"
    docker push "${REGISTRY}/corna-nginx:${TAG}"
}


record_push() {
    local tmp_file

    tmp_file="$(mktemp)"

    awk \
        -v version="${TAG}" \
        -v commit="${COMMIT}" \
        '
        /^PUSHED_VERSION=/ {
            print "PUSHED_VERSION=\"" version "\""
            next
        }
        /^PUSHED_COMMIT=/ {
            print "PUSHED_COMMIT=\"" commit "\""
            next
        }
        { print }
        ' \
        "${RELEASE_FILE}" > "${tmp_file}"

    mv "${tmp_file}" "${RELEASE_FILE}"
}


push() {
    validate_push

    validate_images
    push_images

    record_push

    echo "Successfully pushed ${TAG} (${COMMIT:0:7})"
}


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

usage() {
    cat <<'EOF'
Usage:
  ./infra/build.sh build
  ./infra/build.sh push
  ./infra/build.sh release
EOF
}


main() {
    case "${1:-}" in
        build)
            build
            ;;

        push)
            push
            ;;

        release)
            build
            push
            ;;

        *)
            usage
            exit 1
            ;;
    esac
}


main "$@"
