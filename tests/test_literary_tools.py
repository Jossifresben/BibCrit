import pytest
from biblical_core.claude_pipeline import (
    CHIASM_MODEL, SOURCE_MODEL,
    _CHIASM_SYSTEM, _SOURCE_SYSTEM,
)

def test_chiasm_constants_are_importable():
    assert isinstance(CHIASM_MODEL, str) and CHIASM_MODEL
    assert isinstance(_CHIASM_SYSTEM, str) and 'chiasm' in _CHIASM_SYSTEM.lower()

def test_source_constants_are_importable():
    assert isinstance(SOURCE_MODEL, str) and SOURCE_MODEL
    assert isinstance(_SOURCE_SYSTEM, str) and 'source' in _SOURCE_SYSTEM.lower()
