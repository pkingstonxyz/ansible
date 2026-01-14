#!/usr/bin/env bash

set -eux

echo "Testing for proper json error"
ANSIBLE_DISPLAY_TRACEBACK=always ansible-playbook -i ../../inventory attempt_to_load_invalid_json.yml "$@" 2>&1 | grep 'parsing failed: Did not find expected <document start>'

echo "Testing for broken hostvars symlink"
mkdir host_vars
echo "my_var: shouldnt see this" > host_vars/varfile.yml
ln -s host_vars/varfile.yml host_vars/localhost.yml
mv host_vars/varfile.yml host_vars/break_symlink.yml

ANSIBLE_DISPLAY_TRACEBACK=always ansible-playbook -i ../../inventory attempt_to_use_broken_symlink_hostvars.yml "$@" 2>&1 | grep 'localhost.yml points to a broken symlink'

echo PASS
