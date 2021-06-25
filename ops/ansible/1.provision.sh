#!/usr/bin/env bash
set -eu

main() {

    ansible-playbook -i inventory provision.yaml

}

main "$@"
