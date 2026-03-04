"""Pytest configuration and fixtures for DNS IP+ tests."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture
def mock_config_entry():
    """Fixture to provide a mock config entry."""
    return MockConfigEntry(
        domain="dnsipplus",
        data={
            "device_name": "Test Resolver",
            "resolver_address": "192.168.1.1",
            "resolver_port": 53,
        },
        options={
            "query_interval": 60,
            "domain_monitors": [],
        },
    )
