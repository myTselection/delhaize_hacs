"""Sensors for the Delhaize integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BASE_URL, CONF_LANGUAGE, DEFAULT_LANGUAGE, DOMAIN, NAME
from .coordinator import DelhaizeDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class DelhaizeSensorEntityDescription(SensorEntityDescription):
    """Describe a Delhaize sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] = lambda data: {}


SENSOR_DESCRIPTIONS: tuple[DelhaizeSensorEntityDescription, ...] = (
    DelhaizeSensorEntityDescription(
        key="loyalty_points",
        name="Loyalty points",
        icon="mdi:star-circle",
        value_fn=lambda data: _nested(data, "loyalty", "loyaltyPoints", "pointsBalance"),
        attr_fn=lambda data: _without_none(
            {
                "nutriscore_discount": _nested(data, "loyalty", "nutriscoreBalance", "discount"),
                "nutriscore_available_to_save_this_month": _nested(
                    data,
                    "loyalty",
                    "nutriscoreBalance",
                    "availableToSaveThisMonth",
                ),
                "nutriboost_type": _nested(
                    data,
                    "loyalty",
                    "nutriscoreBalance",
                    "currentNutriBoostType",
                ),
            }
        ),
    ),
    DelhaizeSensorEntityDescription(
        key="savings",
        name="Savings",
        icon="mdi:piggy-bank-outline",
        value_fn=lambda data: _nested(
            data,
            "loyalty",
            "savings",
            "periodSavings",
            "totalSavingsAmountFormatted",
        ),
    ),
    DelhaizeSensorEntityDescription(
        key="personal_offers_available",
        name="Personal offers available",
        icon="mdi:ticket-percent-outline",
        value_fn=lambda data: _available_offers(data),
        attr_fn=lambda data: _without_none(
            {
                "total": _nested(data, "personal_offers_count", "totalCount"),
                "activated": _nested(data, "personal_offers_count", "activatedCount"),
                "activation_result": data.get("activation_result"),
                "activation_error": data.get("activation_error"),
            }
        ),
    ),
    DelhaizeSensorEntityDescription(
        key="personal_offers_total",
        name="Personal offers total",
        icon="mdi:ticket-confirmation-outline",
        value_fn=lambda data: _nested(data, "personal_offers_count", "totalCount"),
    ),
    DelhaizeSensorEntityDescription(
        key="personal_offers_activated",
        name="Personal offers activated",
        icon="mdi:ticket-check-outline",
        value_fn=lambda data: _nested(data, "personal_offers_count", "activatedCount"),
    ),
    DelhaizeSensorEntityDescription(
        key="personal_offers_benefit",
        name="Personal offers benefit",
        icon="mdi:currency-eur",
        value_fn=lambda data: _nested(
            data,
            "personal_offers",
            "totalEuroBenefit",
            "formattedValue",
        ),
        attr_fn=lambda data: _without_none(
            {
                "total_points": _nested(data, "personal_offers", "totalPoints"),
                "benefit_value": _nested(data, "personal_offers", "totalEuroBenefit", "value"),
                "currency": _nested(data, "personal_offers", "totalEuroBenefit", "currencyIso"),
                "error": data.get("personal_offers_error"),
            }
        ),
    ),
    DelhaizeSensorEntityDescription(
        key="loyalty_profile",
        name="Loyalty profile",
        icon="mdi:account-star-outline",
        value_fn=lambda data: _nested(data, "customer", "ibizaLoyaltyProfile"),
    ),
    DelhaizeSensorEntityDescription(
        key="account",
        name="Account",
        icon="mdi:account-circle-outline",
        value_fn=lambda data: _nested(data, "customer", "customerType"),
        attr_fn=lambda data: _without_none(
            {
                "uid": _nested(data, "customer", "uid"),
                "customer_id_hash": _nested(data, "customer", "customerIdHash"),
                "first_name": _nested(data, "customer", "firstName"),
                "last_name": _nested(data, "customer", "lastName"),
                "card": _nested(data, "customer", "diplaCard"),
            }
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Delhaize sensors."""
    coordinator: DelhaizeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [DelhaizeSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS]
    )


class DelhaizeSensor(CoordinatorEntity[DelhaizeDataUpdateCoordinator], SensorEntity):
    """A Delhaize account sensor."""

    entity_description: DelhaizeSensorEntityDescription

    def __init__(
        self,
        coordinator: DelhaizeDataUpdateCoordinator,
        description: DelhaizeSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_attribution = "Data provided by delhaize.be"
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=NAME,
            manufacturer="Delhaize",
            configuration_url=(
                f"{BASE_URL}/{coordinator.config_entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)}"
                "/my-account"
            ),
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra sensor attributes."""
        return self.entity_description.attr_fn(self.coordinator.data or {})


def _nested(data: dict[str, Any], *path: str) -> Any:
    """Return a nested value from dict data."""
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _available_offers(data: dict[str, Any]) -> int | None:
    """Return number of inactive personal offers."""
    total = _nested(data, "personal_offers_count", "totalCount")
    activated = _nested(data, "personal_offers_count", "activatedCount")
    try:
        return max(0, int(total or 0) - int(activated or 0))
    except (TypeError, ValueError):
        return None


def _without_none(data: dict[str, Any]) -> dict[str, Any]:
    """Drop attributes with unknown values."""
    return {key: value for key, value in data.items() if value is not None}
