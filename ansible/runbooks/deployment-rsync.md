## Deployment with rsync

This runbook is for deploying with rsync. The general gist is we copy over
all necessary source code and then either build docker on the server or
run the service using systemd.  

We are currently, going down the docker route so, if using rsync, we will
build the docker container(s) on the server and run them via docker-compose.  


For more info on delete options: https://superuser.com/q/156664  
```
rsync \
    --prune-empty-dirs \
    --archive \
    --verbose \
    --compress \
    --delete-after \
    --delete-excluded \
    --progress \
    --partial \
    --exclude=**/__pycache__/ \
    --include=docker-compose.yml \
    --include=gunicorn.logging.ini \
    --include=gunicorn_conf.py \
    --include=logging.ini \
    --include=Makefile \
    --include=nginx.conf \
    --include=requirements.txt \
    --include=yum-deps \
    --include=yum-repos \
    --exclude=.DS_Store \
    --include=dockerfiles/ \
    --include=dockerfiles/** \
    --include=corna/ \
    --include=corna/**/ \
    --include=corna/**/** \
    --include=corna/**.py \
    --exclude=* \
    --dry-run \
    . <username>@<hostname>:/full/path/to/dest
```
