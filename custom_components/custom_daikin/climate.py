"""Adds support for generic thermostat units."""

import asyncio
from collections.abc import Mapping
from datetime import datetime, timedelta
import logging
import math
import time
from typing import Any

import voluptuous as vol

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    PLATFORM_SCHEMA as CLIMATE_PLATFORM_SCHEMA,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    # ATTR_TEMPERATURE,
    EVENT_HOMEASSISTANT_START,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Context,
    CoreState,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device import async_entity_id_to_device
from homeassistant.helpers.entity import CONTEXT_RECENT_TIME_SECONDS
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
)
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.temperature import TemperatureConverter
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CLIMATE_ENTITY,
    CONF_DUR_COOLDOWN,
    CONF_INITIAL_HVAC_MODE,
    CONF_MIN_DUR,
    CONF_NAME,
    CONF_OFF_TOLERANCE,
    CONF_ON_TOLERANCE,
    CONF_PRECISION,
    CONF_TEMP_SENSOR,
    CONF_TEMP_STEP,
    CONF_UNIQUE_ID,
    DEFAULT_NAME,
    DEFAULT_TOLERANCE,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)
_LOGGER.level = logging.DEBUG


PLATFORM_SCHEMA_COMMON = vol.Schema(
    {
        vol.Required(CONF_CLIMATE_ENTITY): cv.entity_id,
        vol.Required(CONF_TEMP_SENSOR): cv.entity_id,
        vol.Optional(CONF_MIN_DUR): cv.positive_time_period,
        vol.Optional(CONF_DUR_COOLDOWN): cv.positive_time_period,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_OFF_TOLERANCE, default=DEFAULT_TOLERANCE): vol.Coerce(float),
        vol.Optional(CONF_ON_TOLERANCE, default=DEFAULT_TOLERANCE): vol.Coerce(float),
        # vol.Optional(CONF_TARGET_TEMP): vol.Coerce(float),
        vol.Optional(CONF_INITIAL_HVAC_MODE): vol.In(
            [HVACMode.COOL, HVACMode.HEAT, HVACMode.OFF]
        ),
        vol.Optional(CONF_PRECISION): vol.All(
            vol.Coerce(float),
            vol.In([PRECISION_TENTHS, PRECISION_HALVES, PRECISION_WHOLE]),
        ),
        vol.Optional(CONF_TEMP_STEP): vol.All(
            vol.In([PRECISION_TENTHS, PRECISION_HALVES, PRECISION_WHOLE])
        ),
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)


PLATFORM_SCHEMA = CLIMATE_PLATFORM_SCHEMA.extend(PLATFORM_SCHEMA_COMMON.schema)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize config entry."""
    await _async_setup_config(
        hass,
        PLATFORM_SCHEMA_COMMON(dict(config_entry.options)),
        config_entry.entry_id,
        async_add_entities,
    )


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the generic thermostat platform."""

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)
    await _async_setup_config(
        hass, config, config.get(CONF_UNIQUE_ID), async_add_entities
    )


async def _async_setup_config(
    hass: HomeAssistant,
    config: Mapping[str, Any],
    unique_id: str | None,
    async_add_entities: AddEntitiesCallback | AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the generic thermostat platform."""

    name: str = config[CONF_NAME]
    climate_entity_id: str = config[CONF_CLIMATE_ENTITY]
    temperature_entity_id: str = config[CONF_TEMP_SENSOR]
    min_cycle_duration: timedelta | None = config.get(CONF_MIN_DUR)
    cycle_cooldown: timedelta | None = config.get(CONF_DUR_COOLDOWN)
    off_tolerance: float = config.get(CONF_OFF_TOLERANCE, DEFAULT_TOLERANCE)
    on_tolerance: float = config.get(CONF_ON_TOLERANCE, DEFAULT_TOLERANCE)
    initial_hvac_mode: HVACMode = config.get(CONF_INITIAL_HVAC_MODE, HVACMode.OFF)
    precision: float | None = config.get(CONF_PRECISION)
    target_temperature_step: float | None = config.get(CONF_TEMP_STEP)
    unit = hass.config.units.temperature_unit

    async_add_entities(
        [
            DaikinControllerClimateEntity(
                hass,
                name=name,
                climate_entity_id=climate_entity_id,
                temperature_entity_id=temperature_entity_id,
                min_cycle_duration=min_cycle_duration,
                cycle_cooldown=cycle_cooldown,
                off_tolerance=off_tolerance,
                on_tolerance=on_tolerance,
                initial_hvac_mode=initial_hvac_mode,
                precision=precision,
                target_temperature_step=target_temperature_step,
                unit=unit,
                unique_id=unique_id,
            )
        ]
    )


class DaikinControllerClimateEntity(ClimateEntity, RestoreEntity):
    """Representation of a Daikin Thermostat Controller device."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        name: str,
        climate_entity_id: str,
        temperature_entity_id: str,
        min_cycle_duration: timedelta | None,
        cycle_cooldown: timedelta | None,
        off_tolerance: float,
        on_tolerance: float,
        initial_hvac_mode: HVACMode | None,
        precision: float | None,
        target_temperature_step: float | None,
        unit: UnitOfTemperature,
        unique_id: str | None,
    ) -> None:
        """Initialize the thermostat."""
        self._attr_name = name

        self._initial_hvac_mode = initial_hvac_mode

        self.climate_entity_id = climate_entity_id
        self.temperature_entity_id = temperature_entity_id
        self.device_entry = async_entity_id_to_device(
            hass,
            climate_entity_id,
        )
        self.min_cycle_duration = min_cycle_duration or timedelta(minutes=15)
        self.cycle_cooldown = cycle_cooldown or timedelta(minutes=10)
        self._off_tolerance = off_tolerance
        self._on_tolerance = on_tolerance
        # Subtract the cooldown so it doesn't impact startup
        self._last_toggled_time = dt_util.utcnow() - max(
            self.cycle_cooldown, self.min_cycle_duration
        )
        self._check_callback: CALLBACK_TYPE | None = None
        # Context ID used to detect our own toggles
        self._last_context_id: str | None = None
        self._attr_precision = precision
        self._attr_target_temperature_step = target_temperature_step or self.precision
        self._attr_hvac_modes = [
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.HEAT_COOL,
            HVACMode.OFF,
        ]
        self._attr_current_temperature: float | None = None
        self._temp_lock = asyncio.Lock()
        self._attr_temperature_unit = unit
        self._attr_unique_id = unique_id
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
        )

        self._attr_preset_mode = PRESET_NONE
        self._attr_preset_modes = [PRESET_NONE]
        self._initialized = False
        self._entity_temperature_unit = None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        # Add listener
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self.temperature_entity_id], self._async_temperature_changed
            )
        )
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self.climate_entity_id], self._async_climate_action_changed
            )
        )
        self.async_on_remove(self._cancel_timers)

        await self._load_initial_state()

        @callback
        def _async_startup(_: Event | None = None) -> None:
            """Init on startup."""
            temperature_state = self.hass.states.get(self.temperature_entity_id)
            if temperature_state and temperature_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                _LOGGER.debug("Update initial temperature: %s", temperature_state.state)
                self._async_update_temp(temperature_state)
                self.async_write_ha_state()
            climate_state = self.hass.states.get(self.climate_entity_id)
            if climate_state and climate_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                _LOGGER.debug("Update initial climate state: %s", climate_state.state)
                self._entity_temperature_unit = climate_state.attributes.get(
                    "temperature_unit",
                    self.temperature_unit,
                )
                self._attr_min_temp = TemperatureConverter.convert(
                    climate_state.attributes.get("min_temp"),
                    self._entity_temperature_unit,
                    self.temperature_unit,
                )
                self._attr_max_temp = TemperatureConverter.convert(
                    climate_state.attributes.get("max_temp"),
                    self._entity_temperature_unit,
                    self.temperature_unit,
                )
                self._async_update_hvac_action(climate_state)
                self.async_write_ha_state()

            if (
                not hasattr(self, "_attr_target_temperature_high")
                or self._attr_target_temperature_high is None
            ):
                self._attr_target_temperature_high = self.max_temp

            if (
                not hasattr(self, "_attr_target_temperature_low")
                or self._attr_target_temperature_low is None
            ):
                self._attr_target_temperature_low = self.min_temp

            self._initialized = True

        if self.hass.state is CoreState.running:
            _async_startup()
        else:
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _async_startup)

    async def _load_initial_state(self) -> None:
        # Check If we have an old state
        if (old_state := await self.async_get_last_state()) is not None:
            if (value := old_state.attributes.get(ATTR_TARGET_TEMP_LOW)) is not None:
                self._attr_target_temperature_low = value

            if (value := old_state.attributes.get(ATTR_TARGET_TEMP_HIGH)) is not None:
                self._attr_target_temperature_high = value

            if old_state.state is not None:
                self._attr_hvac_mode = HVACMode(old_state.state)

        if not hasattr(self, "_attr_hvac_mode") or self._attr_hvac_mode is None:
            self._attr_hvac_mode = self._initial_hvac_mode

        _LOGGER.debug(
            "Loaded as initial state: target_low=%s, target_high=%s, hvac_mode=%s",
            self.target_temperature_low,
            self.target_temperature_high,
            self.hvac_mode,
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set hvac mode."""
        if hvac_mode not in self.hvac_modes:
            _LOGGER.error("Unsupported hvac mode: %s", hvac_mode)
            return

        _LOGGER.debug("HVAC mode updated to: %s", hvac_mode)
        self._attr_hvac_mode = hvac_mode

        # User requested mode change, reset toggle time to ignore cycle cooldowns
        self._last_toggled_time = dt_util.utcnow() - max(
            self.cycle_cooldown, self.min_cycle_duration
        )

        if hvac_mode in [HVACMode.HEAT, HVACMode.HEAT_COOL, HVACMode.COOL]:
            await self._async_control_hvac(from_user=True)
        elif hvac_mode == HVACMode.FAN_ONLY:
            await self._async_set_climate_hvac_mode(HVACMode.FAN_ONLY)
        elif hvac_mode == HVACMode.OFF:
            await self._async_set_climate_hvac_mode(HVACMode.OFF)

        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        # if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
        #     self._attr_target_temperature = temperature
        _LOGGER.debug(
            "Target temperature updated to: {%s}",
            ", ".join([f"{k}={v!r}" for k, v in kwargs.items()]),
        )

        if (temp_low := kwargs.get(ATTR_TARGET_TEMP_LOW)) is not None and (
            temp_high := kwargs.get(ATTR_TARGET_TEMP_HIGH)
        ) is not None:
            _LOGGER.debug("Temperature updated to: [%s, %s]", temp_low, temp_high)
            self._attr_target_temperature_low = float(temp_low)
            self._attr_target_temperature_high = float(temp_high)

        if (hvac_mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            await self.async_set_hvac_mode(hvac_mode)
            return

        await self._async_control_hvac(from_user=True)
        self.async_write_ha_state()

    async def _async_temperature_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Handle temperature changes."""
        new_state = event.data["new_state"]
        if (
            not self._initialized
            or new_state is None
            or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)
        ):
            return

        self.async_set_context(event.context)
        self._async_update_temp(new_state)
        await self._async_control_hvac()
        self.async_write_ha_state()

    @callback
    def _async_update_temp(self, state: State) -> None:
        """Update thermostat with latest state from sensor."""
        _LOGGER.debug(
            "Current temperature updated to: %s, [%s]",
            state.state,
            ", ".join([f"{k}={v!r}" for k, v in state.attributes.items()]),
        )
        try:
            cur_temp = float(state.state)
            if not math.isfinite(cur_temp):
                raise ValueError(f"Sensor has illegal state {state.state}")  # noqa: TRY301

            self._attr_current_temperature = TemperatureConverter.convert(
                cur_temp,
                state.attributes.get("unit_of_measurement"),
                self.temperature_unit,
            )
        except ValueError as ex:
            _LOGGER.error("Unable to update from sensor: %s", ex)

    async def _async_climate_action_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Handle wrapped climate entity state changes."""
        new_state = event.data["new_state"]
        old_state = event.data["old_state"]
        if (
            not self._initialized
            or new_state is None
            or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)
            or new_state.state == old_state.state
        ):
            return

        self.async_set_context(event.context)
        self._async_update_hvac_action(new_state)
        await self._async_control_hvac()

        _LOGGER.debug("Updating last cycle time to: %s", new_state.last_changed)
        self._last_toggled_time = new_state.last_changed

        self.async_write_ha_state()

    @callback
    def _async_update_hvac_action(self, state: State) -> None:
        _LOGGER.debug(
            "Daikin updated to: %s, [%s]",
            state.state,
            ", ".join([f"{k}={v!r}" for k, v in state.attributes.items()]),
        )
        try:
            cur_mode = HVACMode(state.state)
            match cur_mode:
                case HVACMode.OFF:
                    self._attr_hvac_action = (
                        HVACAction.OFF
                        if self.hvac_mode == HVACMode.OFF
                        else HVACAction.IDLE
                    )
                case HVACMode.HEAT:
                    self._attr_hvac_action = HVACAction.HEATING
                case HVACMode.COOL:
                    self._attr_hvac_action = HVACAction.COOLING
                case _:
                    self._attr_hvac_action = HVACAction.UNAVAILABLE
        except ValueError as ex:
            _LOGGER.error("Unable to update from climate entity: %s", ex)

    async def _async_control_hvac(self, from_user: bool = False) -> None:
        """Check if we need to turn heating on or off."""
        async with self._temp_lock:
            if None in (
                self.current_temperature,
                # self._attr_target_temperature,
                self.target_temperature_low,
                self.target_temperature_high,
            ):
                return

            if self.hvac_mode == HVACMode.OFF:
                if self.hvac_action != HVACAction.OFF:
                    _LOGGER.debug(
                        "Turning off heater %s due to hvac mode off",
                        self.climate_entity_id,
                    )
                    await self._async_set_climate_hvac_mode(HVACMode.OFF)
                return

            _LOGGER.debug(
                "Evaluating current state: %s in %s[%s, %s]",
                self.current_temperature,
                self.hvac_mode,
                self.target_temperature_low,
                self.target_temperature_high,
            )
            _LOGGER.debug(
                "With tollarances: %s & %s", self._on_tolerance, self._off_tolerance
            )
            # Purposly offset differently to avoid rapid on/off cycling when the temperature is around the target range
            too_cold = (
                self.target_temperature_low - self._on_tolerance
            ) > self.current_temperature
            too_hot = (
                self.target_temperature_high + self._on_tolerance
            ) < self.current_temperature
            just_right = (
                (self.target_temperature_low + self._off_tolerance)
                <= self.current_temperature
                <= (self.target_temperature_high - self._off_tolerance)
            )

            now = dt_util.utcnow()

            if not from_user and self.hvac_action in [
                HVACAction.HEATING,
                HVACAction.COOLING,
            ]:
                # Make sure it's past the `min_cycle_duration` before changing state
                min_cycle_target = self._last_toggled_time + self.min_cycle_duration
                if min_cycle_target > now:
                    _LOGGER.debug(
                        "Minimum cycle time of %s not reached, check again at %s",
                        self.min_cycle_duration,
                        min_cycle_target,
                    )
                    self._check_callback = async_call_later(
                        self.hass,
                        min_cycle_target - now,
                        self._async_timer_control_hvac,
                    )
                    return

            if not from_user and self.hvac_action == HVACAction.IDLE:
                # Make sure it's past the `cycle_cooldown` before turning on
                min_cooldown_target = self._last_toggled_time + self.cycle_cooldown
                if min_cooldown_target > now:
                    _LOGGER.debug(
                        "Cooldown time of %s not reached, check again at %s",
                        self.cycle_cooldown,
                        min_cooldown_target,
                    )
                    self._check_callback = async_call_later(
                        self.hass,
                        min_cooldown_target - now,
                        self._async_timer_control_hvac,
                    )
                    return

            if (
                (too_cold or self.hvac_mode == HVACMode.HEAT)
                and self.hvac_action == HVACAction.COOLING
            ) or (
                (too_hot or self.hvac_mode == HVACMode.COOL)
                and self.hvac_action == HVACAction.HEATING
            ):
                # If we're currently running but something changed, and we need to switch modes,
                # turn off to cycle_cooldown before switching modes to avoid damaging the compressor
                _LOGGER.debug(
                    "Switching modes, turning off HVAC %s", self.climate_entity_id
                )
                await self._async_set_climate_hvac_mode(HVACMode.OFF)
                self._check_callback = async_call_later(
                    self.hass,
                    self.cycle_cooldown,
                    self._async_timer_control_hvac,
                )
                return

            if self.hvac_action == HVACAction.HEATING and too_cold:
                _LOGGER.debug("Currently too cold but heating, nothing to do")

            elif self.hvac_action == HVACAction.COOLING and too_hot:
                _LOGGER.debug("Currently too hot but cooling, nothing to do")

            elif (
                just_right
                or (
                    self.hvac_action == HVACAction.HEATING
                    and self.hvac_mode not in [HVACMode.HEAT, HVACMode.HEAT_COOL]
                )
                or (
                    self.hvac_action == HVACAction.COOLING
                    and self.hvac_mode not in [HVACMode.COOL, HVACMode.HEAT_COOL]
                )
            ):
                _LOGGER.debug("Turning off heater %s", self.climate_entity_id)
                await self._async_set_climate_hvac_mode(HVACMode.OFF)

            elif too_cold and self.hvac_mode in [
                HVACMode.HEAT,
                HVACMode.HEAT_COOL,
            ]:
                _LOGGER.debug("Turning on heater %s", self.climate_entity_id)
                await self._async_set_climate_hvac_mode(HVACMode.HEAT)

            elif too_hot and self.hvac_mode in [
                HVACMode.COOL,
                HVACMode.HEAT_COOL,
            ]:
                _LOGGER.debug("Turning on cooler %s", self.climate_entity_id)
                await self._async_set_climate_hvac_mode(HVACMode.COOL)
            else:
                _LOGGER.debug(
                    "NOOP: Temperature is %s but HVAC mode is %s with action %s",
                    self.current_temperature,
                    self.hvac_mode,
                    self.hvac_action,
                )

    def _get_current_context(self) -> Context | None:
        """Return the current context if it is still recent, or None."""
        if (
            self._context_set is not None
            and time.time() - self._context_set > CONTEXT_RECENT_TIME_SECONDS
        ):
            self._context = None
            self._context_set = None
        return self._context

    async def _async_set_climate_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        _LOGGER.debug(
            "Setting daikin to: hvac_mode=%s",
            hvac_mode,
        )

        data = {ATTR_ENTITY_ID: self.climate_entity_id, ATTR_HVAC_MODE: hvac_mode}
        # Create a child context for the switch service call so we can
        # identify the resulting state change event as originating from us.
        # Don't set it as our own context — the climate entity's state changes
        # should remain attributed to the parent context (e.g., set_hvac_mode).
        current_context = self._get_current_context()
        new_context = Context(parent_id=current_context.id if current_context else None)
        self._last_context_id = new_context.id

        if hvac_mode in [HVACMode.HEAT, HVACMode.COOL]:
            data[ATTR_TEMPERATURE] = (
                self.min_temp if hvac_mode == HVACMode.COOL else self.max_temp
            )
            if (
                self._entity_temperature_unit is not None
                and self._entity_temperature_unit != self.temperature_unit
            ):
                data[ATTR_TEMPERATURE] = TemperatureConverter.convert(
                    data[ATTR_TEMPERATURE],
                    self.temperature_unit,
                    self._entity_temperature_unit,
                )
            await self.hass.services.async_call(
                "climate", "set_temperature", data, context=new_context
            )
        else:
            await self.hass.services.async_call(
                "climate", "set_hvac_mode", data, context=new_context
            )

        # TODO: Maybe check if it actually toggled
        self._last_toggled_time = dt_util.utcnow()
        _LOGGER.debug(
            "Updating last cycle time by action to: %s", self._last_toggled_time
        )
        self._cancel_check_timer()

    async def _async_timer_control_hvac(self, _: datetime | None = None) -> None:
        """Reset check timer and control heating."""
        self._check_callback = None
        await self._async_control_hvac()

    @callback
    def _cancel_check_timer(self) -> None:
        """Reset check timer."""
        if self._check_callback:
            _LOGGER.debug("Cancelling scheduled state check")
            self._check_callback()
            self._check_callback = None

    @callback
    def _cancel_timers(self) -> None:
        """Reset timers."""
        self._cancel_check_timer()
