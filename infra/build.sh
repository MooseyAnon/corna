#!/usr/bin/env bash

set -euo pipefail

# this script should be called from project root i.e. ./ansible/build.sh

check_envvars() {
    echo "checking env vars"
    # we want to ensure all env vars are set correctly before running script
    test -n "${PROJECT_ROOT}" || \
        echo "envvar error: PROJECT_ROOT not found" && exit 33

    test -n "${ANSIBLE_VAULT_PASSWORD_FILE}" || \
        echo "envvar error: ANSIBLE_VAULT_PASSWORD_FILE not found" && exit 34

    echo "finished checking env vars"
}


remove_certs() {
    for file in "fullchain" "private"; do
        local full_name="tmp_${file}.pem"
        echo "${full_name}"
        if [ -f "${full_name}" ]; then
            rm "${full_name}"
        fi
    done
}


remove_tags() {
    docker image rmi \
        registry.digitalocean.com/corna-docker-reg/corna:$TAG
    docker image rmi \
        registry.digitalocean.com/corna-docker-reg/corna-nginx:$TAG
}


remove_js_artifacts() {
    echo "Deleting js artifacts..."
    # delete non-es{5,6} files
    # useful cheetsheat on find: \
    #    - https://math2001.github.io/article/bashs-find-command/
    find $PROJECT_ROOT/frontend/public/scripts \
        -not -name "*es5*" \
        -and  -not -name "*es6*" \
        -type f \
        -delete
}


remove_node() {
    if [ -d $PROJECT_ROOT/frontend/node_modules ]; then
        rm -r $PROJECT_ROOT/frontend/node_modules
    fi
    # remove js files
    remove_js_artifacts
}


remove_venv() {
    if [ -d $PROJECT_ROOT/venv ]; then
        rm -r $PROJECT_ROOT/venv
    fi
}


ensure_venv() {
    echo "checking for venv"
    if [ ! -d "${PROJECT_ROOT}/venv" ]; then
        echo "creating venv"
        "${PYTHON}" -m venv venv
        "${PROJECT_ROOT}/venv/bin/python" -m pip install --upgrade pip
    fi
}


install_package() {
    echo "using venv to install $1"
    
    if ! ensure_venv ; then
        echo "there was an issue creating venv"
        exit 1
    fi
    venv/bin/python -m pip install $1 &> /dev/null
}


tmp_certs() {
    echo "saving tmp certs"
    if ! install_package ansible==2.10.7 ; then
        echo "issue installing ansible"
        exit 1
    fi
    local filename="${PROJECT_ROOT}/tmp_${1}.pem"
    ANSIBLE_VAULT_PATH="${PROJECT_ROOT}/corna/utils/vault" \
    ANSIBLE_VAULT_PASSWORD_FILE="${ANSIBLE_VAULT_PASSWORD_FILE}" \
    venv/bin/python -c \
        "import corna.utils as utils; print(utils.vault_item('keys.ssl-certs.${1}'))" \
        >> "${filename}"

    if [[ ! $? -eq 0 ]]; then
        echo "Error running vault for ${1} key"
        exit 1
    fi

    chmod 600 "${filename}"
}


# build main container for CI
build_ci_container() {
    if docker inspect corna-ci:$TAG &> /dev/null ; then
        echo "Found prexisting container, skipping build"
    elif ! docker build -f $DOCKERFILES/Dockerfile-corna -t corna-ci:$TAG . ; then
        echo "There was an issue building the CI image"
        exit 1
    fi
}

# run CI
run_ci() {
    if ! docker run --rm corna-ci:$TAG make check ; then
        echo "ERROR: CI has failed!!"
        exit 1
    fi
}


run_eslint() {
    if [ ! -d $PROJECT_ROOT/frontend/node_modules ]; then
        echo "ERROR: Can not run eslint because node_modules not found"
        exit 1
    fi

    if ! npm run lint --prefix $PROJECT_ROOT/frontend ; then
        echo "ERROR: ESLINT FAIL!!"
        exit 1
    fi

    echo "ESLINT PASSED!!"
}


# Compile typescript and rollup
compile_typescript() {
    # build node_modules if needed
    if [ ! -d $PROJECT_ROOT/frontend/node_modules ]; then
        npm install --prefix $PROJECT_ROOT/frontend
    fi

    run_eslint

    if ! npm run build --prefix $PROJECT_ROOT/frontend ; then
        echo "Failed to compile JS"
        exit 1
    fi
}


# build nginx container
build_nginx_continer() {
    if ! docker inspect corna-nginx:$TAG &> /dev/null ; then
        tmp_certs "fullchain"
        tmp_certs "private"

        if ! docker build -f $DOCKERFILES/Dockerfile-nginx -t corna-nginx:$TAG .; then
            echo "Problem building nginx image"
            exit 1
        fi
    else
        echo "nginx container already exists"
    fi
}


tag_and_push_corna_container() {
    # the ci container is the same container as the main app
    # we need to re-tag it for use with our private docker reg.
    docker tag \
        corna-ci:$TAG \
        registry.digitalocean.com/corna-docker-reg/corna:$TAG    
    if [[ $? -ne 0 ]]; then
        echo "There was a problem tagging corna image"
        exit 1
    fi

    if ! docker push registry.digitalocean.com/corna-docker-reg/corna:$TAG; then
        echo "Could not push corna image to registry"
        exit 1
    fi
}


tag_and_push_nginx_container() {
    docker tag \
        corna-nginx:$TAG \
        registry.digitalocean.com/corna-docker-reg/corna-nginx:$TAG
    if [[ $? -ne 0 ]]; then
        echo "There was a problem tagging the nginx image"
        exit 1
    fi

    if ! docker push registry.digitalocean.com/corna-docker-reg/corna-nginx:$TAG; then
        echo "Could not push the nginx image to registry"
        exit 1
    fi    
}

TAG=${1}
# PROJECT_ROOT is an envvar
DOCKERFILES=$PROJECT_ROOT/dockerfiles
PYTHON=python3.12


build() {
    build_ci_container
    run_ci
    # The reason we compile our js after building main contianer is
    # because our nginx container is where all our none HTML static
    # files live and are served from, we do not need them to be in
    # the main backend container.
    compile_typescript
    build_nginx_continer
    tag_and_push_corna_container
    tag_and_push_nginx_container
}


clean() {
    remove_certs
    remove_tags
    remove_node
    remove_venv    

}

# run build process
build
clean
