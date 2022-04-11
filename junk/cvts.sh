function cvts_prefunc() {
    unset "${!CVTS_@}"
    export CVTS_WORK_PATH=/mnt/data/cvts
    export CVTS_BOUNDARIES_PATH=/mnt/data/cvts/boundaries
    export CVTS_POSTGRES_PORT=5432
    export CVTS_POSTGRES_PASS=csiro_and_world_bank
    export CVTS_RAW_DATA_FORMAT=GZIP
}

function cvts_postfunc() {
    export CVTS_POSTGRES_USER=$CVTS_POSTGRES_DB
    export CVTS_POSTGRES_CONNECTION_STRING=postgresql://"$CVTS_POSTGRES_USER":"$CVTS_POSTGRES_PASS"@"$CVTS_POSTGRES_HOST":"$CVTS_POSTGRES_PORT"/"$CVTS_POSTGRES_DB"
}

function cvts () {
    cvts_prefunc
    export CVTS_DEBUG=False
    export CVTS_OUTPUT_PATH="$CVTS_WORK_PATH"/output
    export CVTS_POSTGRES_DB=cvts
    
    #export CVTS_POSTGRES_HOST=10.100.0.50
    export CVTS_POSTGRES_HOST=localhost
}

function cvts_test() {
    cvts_prefunc
    export CVTS_DEBUG=True
    export CVTS_OUTPUT_PATH="$CVTS_WORK_PATH"/test_output
    export CVTS_POSTGRES_DB=cvts_test

    #export CVTS_RAW_PATH="$CVTS_WORK_PATH"/2017/raw
    #export CVTS_RAW_DATA_FORMAT=CSV

    export CVTS_POSTGRES_USER=$CVTS_POSTGRES_DB
    export CVTS_POSTGRES_HOST=localhost
    export CVTS_POSTGRES_CONNECTION_STRING=postgresql://"$CVTS_POSTGRES_USER":"$CVTS_POSTGRES_PASS"@"$CVTS_POSTGRES_HOST":"$CVTS_POSTGRES_PORT"/"$CVTS_POSTGRES_DB"
    eval $(cvts && python cvts/settings.py)
}

cvts_test
