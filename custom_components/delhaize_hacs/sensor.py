"""Sensors for the Delhaize integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

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
                "activation_refresh_error": data.get("activation_refresh_error"),
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
        icon="mdi:offer",
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
        account_label = _account_label(coordinator)
        device_name = _device_name(account_label)
        object_id_prefix = slugify(device_name) or (
            f"{DOMAIN}_{coordinator.config_entry.entry_id}"
        )

        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_suggested_object_id = f"{object_id_prefix}_{description.key}"
        self._attr_attribution = "Data provided by delhaize.be"
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=device_name,
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


def _account_label(coordinator: DelhaizeDataUpdateCoordinator) -> str:
    """Return the best available label for one Delhaize account."""
    data = coordinator.data or {}
    customer = data.get("customer") if isinstance(data.get("customer"), dict) else {}

    full_name = " ".join(
        value
        for value in (
            _clean_label(customer.get("firstName")),
            _clean_label(customer.get("lastName")),
        )
        if value
    ).strip()
    if full_name:
        return full_name

    title = _clean_label(coordinator.config_entry.title)
    if title and title.lower() != NAME.lower():
        title_prefix = f"{NAME} "
        if title.lower().startswith(title_prefix.lower()):
            return title[len(title_prefix) :].strip() or title
        return title

    username = _clean_label(coordinator.config_entry.data.get(CONF_USERNAME))
    if username:
        return username

    for value in (
        customer.get("customerIdHash"),
        customer.get("uid"),
        coordinator.config_entry.unique_id,
    ):
        label = _clean_label(value)
        if label:
            return f"Account {label[-8:]}"

    return f"Account {coordinator.config_entry.entry_id[:8]}"


def _device_name(account_label: str) -> str:
    """Return a Home Assistant device name for one Delhaize account."""
    label = account_label.lower()
    if label == NAME.lower() or label.startswith(f"{NAME.lower()} "):
        return account_label
    return f"{NAME} {account_label}"


def _clean_label(value: Any) -> str | None:
    """Return a stripped non-empty string."""
    if value is None:
        return None
    label = str(value).strip()
    return label or None
