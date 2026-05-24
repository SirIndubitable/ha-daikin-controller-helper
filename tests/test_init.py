"""Test the My Daikin Controller integration."""

import pytest

from homeassistant.components.custom_daikin.const import DOMAIN
from homeassistant.components.climate.const import ClimateEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry


@pytest.mark.parametrize("platform", ["climate"])
async def test_setup_and_remove_config_entry(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    platform: str,
) -> None:
    """Test setting up and removing a config entry."""
    input_climate_entity_id = "climate.input"
    custom_daikin_entity_id = f"{platform}.my_custom_daikin"

    hass.states.async_set(
        input_climate_entity_id,
        "heat",
        {
            "current_temperature": 21.0,
            "temperature": 23.0,
            "hvac_modes": ["off", "heat", "cool"],
            "supported_features": int(ClimateEntityFeature.TARGET_TEMPERATURE),
            "temperature_unit": "C",
        },
    )

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "entity_id": input_climate_entity_id,
            "name": "My custom_daikin",
        },
        title="My custom_daikin",
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check the entity is registered in the entity registry
    assert entity_registry.async_get(custom_daikin_entity_id) is not None

    # Check the platform is setup correctly
    state = hass.states.get(custom_daikin_entity_id)
    assert state.state == "heat"
    assert state.attributes["source_entity_id"] == input_climate_entity_id
    assert state.attributes["temperature"] == 23.0

    # Remove the config entry
    assert await hass.config_entries.async_remove(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check the state and entity registry entry are removed
    assert hass.states.get(custom_daikin_entity_id) is None
    assert entity_registry.async_get(custom_daikin_entity_id) is None
