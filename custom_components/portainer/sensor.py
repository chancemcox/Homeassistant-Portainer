"""Portainer container status sensor."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import CONF_CONTAINER_NAME, DATA_MANAGER, DOMAIN
from .docker_manager import PortainerDockerManager

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Portainer sensors from a config entry."""
    manager: PortainerDockerManager = hass.data[DOMAIN][entry.entry_id][DATA_MANAGER]

    async def async_update_data() -> dict[str, Any]:
        try:
            info = await manager.async_status()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error fetching Portainer status: {err}") from err
        if info is None:
            return {"status": "missing", "image": manager.image}
        state = info.get("State", {})
        return {
            "status": state.get("Status", "unknown"),
            "running": bool(state.get("Running")),
            "started_at": state.get("StartedAt"),
            "image": info.get("Config", {}).get("Image", manager.image),
            "container_id": info.get("Id", "")[:12],
        }

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{entry.entry_id}",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([PortainerStatusSensor(coordinator, entry)])


class PortainerStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor exposing the managed Portainer container status."""

    _attr_has_entity_name = True
    _attr_name = "Container status"
    _attr_icon = "mdi:docker"

    def __init__(
        self, coordinator: DataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the status sensor."""
        super().__init__(coordinator)
        container_name = entry.data.get(CONF_CONTAINER_NAME, "portainer")
        self._attr_unique_id = f"{entry.entry_id}_container_status"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Portainer",
            "manufacturer": "Portainer",
            "model": "Community Edition",
            "sw_version": entry.data.get("image"),
        }
        self._container_name = container_name

    @property
    def native_value(self) -> str | None:
        """Return the container status string."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("status")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional container details."""
        data = self.coordinator.data or {}
        return {
            "container_name": self._container_name,
            "image": data.get("image"),
            "container_id": data.get("container_id"),
            "started_at": data.get("started_at"),
            "running": data.get("running"),
        }
