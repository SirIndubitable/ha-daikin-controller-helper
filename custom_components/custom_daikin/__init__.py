"""The My Daikin Controller integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import _LOGGER, Event, HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_entity_registry_updated_event

from .const import CONF_CLIMATE_ENTITY, CONF_TEMP_SENSOR


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up My Daikin Controller from a config entry."""

    async def async_hvac_updated(
        event: Event[er.EventEntityRegistryUpdatedData],
    ) -> None:
        """Handle entity registry update."""
        data = event.data
        if data["action"] != "update":
            return
        if "entity_id" not in data["changes"]:
            return

        # Entity_id changed, update the config entry
        hass.config_entries.async_update_entry(
            entry,
            options={**entry.options, CONF_CLIMATE_ENTITY: data["entity_id"]},
        )
        hass.config_entries.async_schedule_reload(entry.entry_id)

    entry.async_on_unload(
        async_track_entity_registry_updated_event(
            hass, entry.options[CONF_CLIMATE_ENTITY], async_hvac_updated
        )
    )

    async def async_sensor_updated(
        event: Event[er.EventEntityRegistryUpdatedData],
    ) -> None:
        """Handle entity registry update."""
        data = event.data
        if data["action"] != "update":
            return
        if "entity_id" not in data["changes"]:
            return

        # Entity_id changed, update the config entry
        hass.config_entries.async_update_entry(
            entry,
            options={**entry.options, CONF_TEMP_SENSOR: data["entity_id"]},
        )
        hass.config_entries.async_schedule_reload(entry.entry_id)

    entry.async_on_unload(
        async_track_entity_registry_updated_event(
            hass, entry.options[CONF_TEMP_SENSOR], async_sensor_updated
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, (Platform.CLIMATE,))
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug(
        "Migrating from version %s.%s", config_entry.version, config_entry.minor_version
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, (Platform.CLIMATE,))
