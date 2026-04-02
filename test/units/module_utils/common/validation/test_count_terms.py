# -*- coding: utf-8 -*-
# Copyright (c) 2019 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import pytest

from ansible.module_utils.common.sentinel import OMITTED
from ansible.module_utils.common.validation import count_terms


@pytest.fixture
def params():
    return {
        'name': 'bob',
        'dest': '/etc/hosts',
        'state': 'present',
        'value': 5,
    }


def test_count_terms(params):
    check = set(('name', 'dest'))
    assert count_terms(check, params) == 2


def test_count_terms_str_input(params):
    check = 'name'
    assert count_terms(check, params) == 1


def test_count_terms_tuple_input(params):
    check = ('name', 'dest')
    assert count_terms(check, params) == 2


def test_count_terms_list_input(params):
    check = ['name', 'dest']
    assert count_terms(check, params) == 2


def test_count_terms_with_omitted():
    """Test that OMITTED values are not counted."""
    params_with_omitted = {
        'name': 'bob',
        'dest': OMITTED,
        'state': 'present',
    }
    check = ('name', 'dest')
    # Only 'name' should be counted, 'dest' is OMITTED
    assert count_terms(check, params_with_omitted) == 1


def test_count_terms_with_none_vs_omitted():
    """Test that None values are counted but OMITTED values are not."""
    params_with_both = {
        'name': None,
        'dest': OMITTED,
        'state': 'present',
    }
    check = ('name', 'dest', 'state')
    # 'name' (None) and 'state' should be counted, 'dest' (OMITTED) should not
    assert count_terms(check, params_with_both) == 2


def test_count_terms_all_omitted():
    """Test that all OMITTED values returns zero count."""
    params_all_omitted = {
        'name': OMITTED,
        'dest': OMITTED,
    }
    check = ('name', 'dest')
    assert count_terms(check, params_all_omitted) == 0
