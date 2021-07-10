#!/bin/bash

# ensure env varibles are set (... assuming they are define in...)
. ~/.bash_aliases

# kill and remove any existing container
docker kill cvts-postgres
docker rm cvts-postgres

## use or create the host folder (probably not required)
#if [[ -z "${CVTS_HOST_DATA_DIR}" ]]; then
#    CVTS_HOST_DATA_DIR=/tmp/postgre-docker-testing
#    rm -rf "$CVTS_HOST_DATA_DIR"
#    mkdir "$CVTS_HOST_DATA_DIR"
#fi

docker run -d \
    --name cvts-postgres \
    -e PGDATA=/var/lib/postgresql/data \
    -e POSTGRES_DB="$CVTS_POSTGRES_DB" \
    -e POSTGRES_USER="$CVTS_POSTGRES_USER" \
    -e POSTGRES_PASSWORD="$CVTS_POSTGRES_PASS" \
    -p "$CVTS_POSTGRES_PORT":5432 \
    postgres
#    -v "$CVTS_HOST_DATA_DIR":/var/lib/postgresql/data \

# wait for a few moments to reduced the chance of whatever comes next failing
# because the container has not finished launching
sleep 5
