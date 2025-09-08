import pytest

from src.application.services.application_service_base import ApplicationServiceBase


class DummyService(ApplicationServiceBase):
    pass


def test_validate_input_true_false():
    service = DummyService()
    assert service.validate_input({}) is True
    assert service.validate_input(0) is True
    assert service.validate_input(None) is False


def test_handle_error_returns_string():
    service = DummyService()
    err = ValueError("boom")
    msg = service.handle_error(err)
    assert isinstance(msg, str)
    assert "Service error:" in msg
    assert "boom" in msg


