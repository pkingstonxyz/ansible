# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

from ansible.module_utils.basic import AnsibleModule

import pytest


@pytest.fixture
def set_attrs(am, mocker):
    """Return a callable invoking set_attributes_if_different against a faked lsattr result.

    The callable returns the resulting ``changed`` value along with the operation
    handed to chattr, or ``None`` when chattr was not run.
    """
    mocker.patch.object(AnsibleModule, 'get_bin_path', return_value='/usr/bin/chattr')
    mocker.patch.object(AnsibleModule, 'check_file_absent_if_check_mode', return_value=False)
    run_command = mocker.patch.object(AnsibleModule, 'run_command', return_value=(0, '', ''))

    def call(existing, attributes, diff=None):
        mocker.patch.object(AnsibleModule, 'get_file_attributes', return_value=existing)
        changed = am.set_attributes_if_different('/path/to/file', attributes, False, diff=diff, expand=False)
        operation = run_command.call_args[0][0][1] if run_command.called else None
        return changed, operation

    return call


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_no_attributes_returns_previous_changes(am):
    assert am.set_attributes_if_different('/path/to/file', None, True) is True


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_add_is_passed_through_verbatim(set_attrs):
    # lsattr reports flags chattr cannot set, such as 'I' on an indexed ext4
    # directory, so the existing flags must never reach the command line
    changed, operation = set_attrs({'attr_flags': 'eI'}, '+A')
    assert changed is True
    assert operation == '+A'


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_adding_an_existing_flag_is_not_a_change(set_attrs):
    changed, operation = set_attrs({'attr_flags': 'Ae'}, '+A')
    assert changed is False
    assert operation is None


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_removing_an_absent_flag_is_not_a_change(set_attrs):
    changed, operation = set_attrs({'attr_flags': 'e'}, '-A')
    assert changed is False
    assert operation is None


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_removing_a_present_flag_is_a_change(set_attrs):
    changed, operation = set_attrs({'attr_flags': 'Ae'}, '-A')
    assert changed is True
    assert operation == '-A'


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_removing_an_invalid_flag_is_not_a_change(set_attrs):
    # a flag chattr does not accept is never set, so removing it is already
    # satisfied; adding one is unsatisfiable and still reaches chattr
    changed, operation = set_attrs({'attr_flags': 'A'}, '-Q')
    assert changed is False
    assert operation is None


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_removing_only_passes_the_flags_actually_set(set_attrs):
    changed, operation = set_attrs({'attr_flags': 'Ae'}, '-AQ')
    assert changed is True
    assert operation == '-A'


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_removing_flags_none_of_which_are_set_runs_no_command(set_attrs):
    changed, operation = set_attrs({'attr_flags': 'e'}, '-AQ')
    assert changed is False
    assert operation is None


@pytest.mark.parametrize('attributes', ['+P', '+F', '+x'])
@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_less_common_flags_are_passed_through(set_attrs, attributes):
    # these were silently dropped while user input was filtered through FILE_ATTRIBUTES
    changed, operation = set_attrs({'attr_flags': ''}, attributes)
    assert changed is True
    assert operation == attributes


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_unrecognized_flags_warn(mocker, set_attrs):
    warn = mocker.patch.object(AnsibleModule, 'warn')
    changed, operation = set_attrs({'attr_flags': 'Ae'}, '-AQ')
    assert warn.called
    assert 'Q' in warn.call_args[0][0]
    # the warning is diagnostic only; the satisfiable part is still applied
    assert changed is True
    assert operation == '-A'


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_recognized_but_unset_flags_do_not_warn(mocker, set_attrs):
    # 'd' is a real attribute which simply is not set, so there is nothing to report
    warn = mocker.patch.object(AnsibleModule, 'warn')
    changed, operation = set_attrs({'attr_flags': 'A'}, '-d')
    assert changed is False
    assert operation is None
    assert not warn.called


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_unreadable_attributes_are_applied_unconditionally(set_attrs):
    # without the current flags no change can be detected, so the requested
    # operation is run regardless
    changed, operation = set_attrs({}, '-A')
    assert changed is True
    assert operation == '-A'


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_unreadable_attributes_warn(mocker, set_attrs):
    warn = mocker.patch.object(AnsibleModule, 'warn')
    set_attrs({}, '-A')
    assert warn.called


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_empty_attributes_clear_the_existing_ones(set_attrs):
    # '=' is the default operator, so an empty value asks for no attributes at all
    changed, operation = set_attrs({'attr_flags': 'ia'}, '')
    assert changed is True
    assert operation == '='


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_empty_attributes_are_not_a_change_when_none_are_set(set_attrs):
    changed, operation = set_attrs({'attr_flags': ''}, '')
    assert changed is False
    assert operation is None


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_empty_attributes_do_nothing_when_unreadable(mocker, set_attrs):
    # preserved_copy passes the source flags verbatim, which may be empty
    warn = mocker.patch.object(AnsibleModule, 'warn')
    changed, operation = set_attrs({}, '')
    assert changed is False
    assert operation is None
    assert not warn.called


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_diff_sides_share_lsattr_ordering(set_attrs):
    # 'before' is the lsattr output verbatim and 'after' is ordered to match
    # it, so the two can be compared directly; note 'dA' is lsattr order
    # while 'Ad' is alphabetical
    diff = {}
    set_attrs({'attr_flags': 'dA'}, '+e', diff=diff)
    assert diff['before']['attributes'] == 'dA'
    assert diff['after']['attributes'] == 'dAe'


@pytest.mark.parametrize('stdin', [{}], indirect=['stdin'])
def test_diff_before_is_none_when_attributes_are_unreadable(set_attrs):
    diff = {}
    set_attrs({}, '+A', diff=diff)
    assert diff['before']['attributes'] is None
    assert diff['after']['attributes'] == 'A'
