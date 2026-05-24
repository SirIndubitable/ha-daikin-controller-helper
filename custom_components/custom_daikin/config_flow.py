"""Config flow for the My Daikin Controller integration."""

from collections.abc import Mapping
from typing import Any, cast

import voluptuous as vol

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN, HVACMode
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.config_entries import CONF_NAME
from homeassistant.const import DEGREE
from homeassistant.helpers import selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaCommonFlowHandler,
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
    SchemaFlowMenuStep,
)

from .const import (
    CONF_CLIMATE_ENTITY,
    CONF_DUR_COOLDOWN,
    CONF_INITIAL_HVAC_MODE,
    CONF_MAX_TEMP,
    CONF_MIN_DUR,
    CONF_MIN_TEMP,
    CONF_OFF_TOLERANCE,
    CONF_ON_TOLERANCE,
    CONF_PRECISION,
    CONF_TEMP_SENSOR,
    CONF_TEMP_STEP,
    DEFAULT_TOLERANCE,
    DOMAIN,
)

OPTIONS_SCHEMA = {
    vol.Required(CONF_CLIMATE_ENTITY): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN)
    ),
    vol.Required(CONF_TEMP_SENSOR): selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=SENSOR_DOMAIN, device_class=SensorDeviceClass.TEMPERATURE
        )
    ),
    vol.Required(CONF_ON_TOLERANCE, default=DEFAULT_TOLERANCE): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, unit_of_measurement=DEGREE, step=0.1
        )
    ),
    vol.Required(
        CONF_OFF_TOLERANCE, default=DEFAULT_TOLERANCE
    ): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, unit_of_measurement=DEGREE, step=0.1
        )
    ),
    vol.Optional(CONF_MIN_DUR): selector.DurationSelector(
        selector.DurationSelectorConfig(allow_negative=False)
    ),
    vol.Optional(CONF_DUR_COOLDOWN): selector.DurationSelector(
        selector.DurationSelectorConfig(allow_negative=False)
    ),
    vol.Optional(CONF_INITIAL_HVAC_MODE): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=HVACMode.HEAT_COOL, label="Auto"),
                selector.SelectOptionDict(value=HVACMode.COOL, label="Cool"),
                selector.SelectOptionDict(value=HVACMode.HEAT, label="Heat"),
                selector.SelectOptionDict(value=HVACMode.OFF, label="Off"),
            ]
        )
    ),
    vol.Optional(CONF_MIN_TEMP): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, unit_of_measurement=DEGREE, step=0.1
        )
    ),
    vol.Optional(CONF_MAX_TEMP): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, unit_of_measurement=DEGREE, step=0.1
        )
    ),
    vol.Optional(CONF_PRECISION): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, unit_of_measurement=DEGREE
        )
    ),
    vol.Optional(CONF_TEMP_STEP): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, unit_of_measurement=DEGREE
        )
    ),
}

CONFIG_SCHEMA = {
    vol.Required(CONF_NAME): selector.TextSelector(),
    **OPTIONS_SCHEMA,
}


async def _validate_config(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate config."""

    return user_input


CONFIG_FLOW: dict[str, SchemaFlowFormStep | SchemaFlowMenuStep] = {
    "user": SchemaFlowFormStep(
        vol.Schema(CONFIG_SCHEMA),
        validate_user_input=_validate_config,
    ),
}

OPTIONS_FLOW: dict[str, SchemaFlowFormStep | SchemaFlowMenuStep] = {
    "init": SchemaFlowFormStep(
        vol.Schema(OPTIONS_SCHEMA),
        validate_user_input=_validate_config,
    ),
}


class ConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config or options flow for My Daikin Controller."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW
    options_flow_reloads = True

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return cast(str, options["name"]) if "name" in options else ""
