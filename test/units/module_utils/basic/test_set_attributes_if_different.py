# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

from ansible.module_utils.basic import AnsibleModule

import pytest


@pytest.fixture
def set_attrs(am, mocker):
    """Return a callable invoking set_attributes_if_different against a faked lsattr result.

    ``existing`` is the flag string lsattr reports, or None when it cannot be read.
    The callable returns the resulting ``changed`` value along with the operation
    handed to chattr, or None when chattr was not run.
    """
    mocker.patch.object(AnsibleModule, 'get_bin_path', return_value='/usr/bin/chattr')
    mocker.patch.object(AnsibleModule, 'check_file_absent_if_check_mode', return_value=False)
    run_command = mocker.patch.object(AnsibleModule, 'run_command', return_value=(0, '', ''))

    def call(existing, attributes, diff=None):
        reported = {} if existing is None else {'attr_flags': existing}
        mocker.patch.object(AnsibleModule, 'get_file_attributes', return_value=reported)
        changed = am.set_attributes_if_different('/path/to/file', attributes, False, diff=diff, expand=False)
        operation = run_command.call_args[0][0][1] if run_command.called else None
        return changed, operation

    return call


# lsattr output, requested attributes, expected change, operation passed to chattr
ATTRIBUTE_CASES = [
    ('eI', '+A', True, '+A'),      # flags lsattr reports but chattr cannot set stay out of the command
    ('Ae', '+A', False, None),     # already set
    ('e', '-A', False, None),      # not set
    ('Ae', '-A', True, '-A'),
    ('Ade', '-A', True, '-A'),     # the other flags are left alone
    ('', '+P', True, '+P'),        # beyond the most common flags
    ('', '+F', True, '+F'),
    ('', '+x', True, '+x'),
    ('A', '-Q', False, None),      # unrecognized, so there is nothing to remove
    ('Ae', '-AQ', True, '-A'),     # only the flags actually set are passed
    ('e', '-AQ', False, None),
    ('ia', '', True, '='),         # '=' is the default operator
    ('', '', False, None),
    (None, '+A', True, '+A'),      # unreadable, so applied unconditionally
    (None, '-A', True, '-A'),
    (None, '', False, None),
]


@pytest.mark.parametrize('existing, attributes, expected_changed, expected_operation', ATTRIBUTE_CASES)
@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_set_attributes(set_attrs, existing, attributes, expected_changed, expected_operation):
    changed, operation = set_attrs(existing, attributes)
    assert changed is expected_changed
    assert operation == expected_operation


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_no_attributes_returns_previous_changes(am):
    assert am.set_attributes_if_different('/path/to/file', None, True) is True


# lsattr output, requested attributes, whether a warning is expected
WARNING_CASES = [
    ('Ae', '-AQ', True),    # 'Q' is not a known attribute
    ('A', '-Q', True),
    (None, '-A', True),     # the current attributes could not be read
    ('A', '-d', False),     # 'd' is a real attribute which simply is not set
    ('e', '+A', False),
    (None, '', False),      # nothing was asked for
]


@pytest.mark.parametrize('existing, attributes, expected', WARNING_CASES)
@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_warnings(mocker, set_attrs, existing, attributes, expected):
    warn = mocker.patch.object(AnsibleModule, 'warn')
    set_attrs(existing, attributes)
    assert warn.called is expected


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_unrecognized_flags_are_named_in_the_warning(mocker, set_attrs):
    warn = mocker.patch.object(AnsibleModule, 'warn')
    set_attrs('Ae', '-AQ')
    assert 'Q' in warn.call_args[0][0]


# lsattr output, requested attributes, diff before, diff after
DIFF_CASES = [
    ('dA', '+e', 'dA', 'dAe'),  # before is verbatim, after is ordered to match it
    (None, '+A', None, 'A'),
]


@pytest.mark.parametrize('existing, attributes, before, after', DIFF_CASES)
@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_diff(set_attrs, existing, attributes, before, after):
    diff = {}
    set_attrs(existing, attributes, diff=diff)
    assert diff['before']['attributes'] == before
    assert diff['after']['attributes'] == after
