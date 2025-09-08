import re
import pytest

from src.domain.value_objects.domain_id import DomainId


def test_domain_id_str_and_value():
    did = DomainId("  abc-123  ")
    assert str(did) == "abc-123"
    assert did.value == "abc-123"
    assert repr(did) == "DomainId('abc-123')"


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_domain_id_invalid_inputs(bad):
    with pytest.raises(ValueError):
        DomainId(bad)  # type: ignore[arg-type]


def test_generate_unique_uuid_like():
    a = DomainId.generate()
    b = DomainId.generate()
    assert a != b
    # crude uuid4 format check
    assert re.fullmatch(r"[0-9a-f\-]{36}", str(a))


def test_from_string_alias():
    did = DomainId.from_string("xyz")
    assert isinstance(did, DomainId)
    assert str(did) == "xyz"


