"""Unit tests for DNS Resolver Monitoring options flow reload functionality."""

import pytest
from homeassistant.config_entries import OptionsFlowWithReload
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dnsipplus.config_flow import DnsResolverMonitoringOptionsFlow
from custom_components.dnsipplus.const import (
    CONF_DEVICE_NAME,
    CONF_DOMAIN_MONITORS,
    CONF_QUERY_INTERVAL,
    CONF_RESOLVER_ADDRESS,
    CONF_RESOLVER_PORT,
    DOMAIN,
)


@pytest.mark.asyncio
class TestDnsResolverMonitoringOptionsFlowReload:
    """Test the DNS Resolver Monitoring options flow reload functionality."""

    async def test_options_flow_extends_reload_base_class(self):
        """
        Test that DnsResolverMonitoringOptionsFlow extends OptionsFlowWithReload.

        This verifies that the options flow will automatically trigger a config entry
        reload when options are saved, satisfying Requirements 11.5 and 7.4.
        """
        # Create a mock config entry
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_DEVICE_NAME: "Test Resolver",
                CONF_RESOLVER_ADDRESS: "192.168.1.1",
                CONF_RESOLVER_PORT: 53,
            },
            options={
                CONF_QUERY_INTERVAL: 60,
                CONF_DOMAIN_MONITORS: [],
            },
        )

        # Create an instance of the options flow (pass config_entry to __init__)
        options_flow = DnsResolverMonitoringOptionsFlow(config_entry)

        # Verify that the options flow is an instance of OptionsFlowWithReload
        assert isinstance(options_flow, OptionsFlowWithReload), (
            "DnsResolverMonitoringOptionsFlow must extend OptionsFlowWithReload to trigger automatic reload"
        )

    async def test_options_flow_save_triggers_reload(self, hass):
        """
        Test that saving options through the options flow triggers a reload.

        This test verifies that when options are saved via async_create_entry,
        the OptionsFlowWithReload base class will automatically trigger a config
        entry reload, applying changes within one query interval period.

        Validates: Requirements 11.5, 7.4
        """
        # Create a mock config entry
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_DEVICE_NAME: "Test Resolver",
                CONF_RESOLVER_ADDRESS: "192.168.1.1",
                CONF_RESOLVER_PORT: 53,
            },
            options={
                CONF_QUERY_INTERVAL: 60,
                CONF_DOMAIN_MONITORS: [],
            },
        )
        config_entry.add_to_hass(hass)

        # Initialize the options flow (pass config_entry to __init__)
        options_flow = DnsResolverMonitoringOptionsFlow(config_entry)
        options_flow.hass = hass
        options_flow.handler = config_entry.entry_id  # Set handler to enable entry_id access

        # Simulate user saving updated options
        result = await options_flow.async_step_init(
            user_input={
                CONF_RESOLVER_ADDRESS: "192.168.1.2",  # Changed address
                CONF_RESOLVER_PORT: 5353,  # Changed port
                CONF_QUERY_INTERVAL: 120,  # Changed interval
                "action": "save",
            }
        )

        # Verify that the options flow returns a CREATE_ENTRY result
        # This triggers the reload via OptionsFlowWithReload
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_QUERY_INTERVAL] == 120
        assert result["data"][CONF_DOMAIN_MONITORS] == []

        # Verify that the config entry data was updated
        assert config_entry.data[CONF_RESOLVER_ADDRESS] == "192.168.1.2"
        assert config_entry.data[CONF_RESOLVER_PORT] == 5353

    async def test_options_flow_preserves_device_name(self, hass):
        """
        Test that the options flow preserves the device name when updating options.

        The device name is stored in the data section and should not be changed
        through the options flow.
        """
        # Create a mock config entry
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_DEVICE_NAME: "Original Device Name",
                CONF_RESOLVER_ADDRESS: "192.168.1.1",
                CONF_RESOLVER_PORT: 53,
            },
            options={
                CONF_QUERY_INTERVAL: 60,
                CONF_DOMAIN_MONITORS: [],
            },
        )
        config_entry.add_to_hass(hass)

        # Initialize the options flow (pass config_entry to __init__)
        options_flow = DnsResolverMonitoringOptionsFlow(config_entry)
        options_flow.hass = hass
        options_flow.handler = config_entry.entry_id  # Set handler to enable entry_id access

        # Simulate user saving updated options
        result = await options_flow.async_step_init(
            user_input={
                CONF_RESOLVER_ADDRESS: "192.168.1.2",
                CONF_RESOLVER_PORT: 53,
                CONF_QUERY_INTERVAL: 120,
                "action": "save",
            }
        )

        # Verify that the device name was preserved
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert config_entry.data[CONF_DEVICE_NAME] == "Original Device Name"

    async def test_options_flow_updates_domain_monitors(self, hass):
        """
        Test that the options flow can update domain monitors.

        This verifies that domain monitors can be added/removed through the
        options flow and the changes will be applied via reload.

        Validates: Requirements 11.4, 11.5
        """
        # Create a mock config entry with existing domain monitors
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_DEVICE_NAME: "Test Resolver",
                CONF_RESOLVER_ADDRESS: "192.168.1.1",
                CONF_RESOLVER_PORT: 53,
            },
            options={
                CONF_QUERY_INTERVAL: 60,
                CONF_DOMAIN_MONITORS: [
                    {"domain": "example.com", "record_type": "A"},
                ],
            },
        )
        config_entry.add_to_hass(hass)

        # Initialize the options flow (pass config_entry to __init__)
        options_flow = DnsResolverMonitoringOptionsFlow(config_entry)
        options_flow.hass = hass
        options_flow.handler = config_entry.entry_id  # Set handler to enable entry_id access

        # First, load the existing monitors
        await options_flow.async_step_init()

        # Add a new domain monitor
        await options_flow.async_step_add_domain(
            user_input={
                "domain": "google.com",
                "record_type": "AAAA",
            }
        )

        # Save the configuration
        result = await options_flow.async_step_init(
            user_input={
                CONF_RESOLVER_ADDRESS: "192.168.1.1",
                CONF_RESOLVER_PORT: 53,
                CONF_QUERY_INTERVAL: 60,
                "action": "save",
            }
        )

        # Verify that the new domain monitor was added
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert len(result["data"][CONF_DOMAIN_MONITORS]) == 2
        assert result["data"][CONF_DOMAIN_MONITORS][0] == {
            "domain": "example.com",
            "record_type": "A",
        }
        assert result["data"][CONF_DOMAIN_MONITORS][1] == {
            "domain": "google.com",
            "record_type": "AAAA",
        }
