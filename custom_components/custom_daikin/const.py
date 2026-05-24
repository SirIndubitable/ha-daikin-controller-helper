"""Constants for the My Daikin Controller integration."""

from homeassistant.const import (
    CONF_NAME,  # noqa: F401
    CONF_UNIQUE_ID,  # noqa: F401
    Platform,
)

DOMAIN = "custom_daikin"

PLATFORMS = [Platform.CLIMATE]

# CONF_TARGET_TEMP = "target_temp"
CONF_CLIMATE_ENTITY = "climate_entity"
CONF_ON_TOLERANCE = "on_tolerance"
CONF_DUR_COOLDOWN = "cycle_cooldown"
CONF_OFF_TOLERANCE = "off_tolerance"
CONF_INITIAL_HVAC_MODE = "initial_hvac_mode"
CONF_MIN_DUR = "min_cycle_duration"
CONF_TEMP_SENSOR = "temperature_sensor"
CONF_PRECISION = "precision"
CONF_TEMP_STEP = "target_temp_step"

DEFAULT_NAME = "Daikin Thermostat Controller"
DEFAULT_TOLERANCE = 0.3
