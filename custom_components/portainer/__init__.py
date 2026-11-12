"""The Portainer integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_STOP_ON_UNLOAD,
    CONF_UI_URL,
    DATA_MANAGER,
    DOMAIN,
)
from .docker_manager import PortainerDockerManager
from .panel import async_setup_panel, async_unload_panel

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Portainer domain (YAML is not supported)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Portainer from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    manager = PortainerDockerManager(hass, dict(entry.data))

    try:
        await manager.async_connect()
        await manager.async_ensure_running()
    except Exception as err:
        await manager.async_close()
        raise ConfigEntryNotReady(f"Unable to start Portainer container: {err}") from err

    hass.data[DOMAIN][entry.entry_id] = {DATA_MANAGER: manager}
    hass.data[DOMAIN][DATA_MANAGER] = manager

    await async_setup_panel(hass, entry.data[CONF_UI_URL])
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    _async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Portainer config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    data = hass.data[DOMAIN].pop(entry.entry_id, {})
    manager: PortainerDockerManager | None = data.get(DATA_MANAGER)

    if manager is not None:
        if entry.data.get(CONF_STOP_ON_UNLOAD, False):
            try:
                await manager.async_stop()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Error stopping Portainer container on unload")
        await manager.async_close()

    if hass.data[DOMAIN].get(DATA_MANAGER) is manager:
        hass.data[DOMAIN].pop(DATA_MANAGER, None)

    # single_config_entry integration: remove the sidebar when unloaded.
    await async_unload_panel(hass)

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, "restart_container"):
        return

    async def async_restart_container(_call: ServiceCall) -> None:
        """Restart the managed Portainer container."""
        manager: PortainerDockerManager | None = hass.data.get(DOMAIN, {}).get(
            DATA_MANAGER
        )
        if manager is None:
            _LOGGER.error("Portainer manager is not available")
            return
        await manager.async_stop()
        await manager.async_ensure_running()

    async def async_start_container(_call: ServiceCall) -> None:
        """Ensure the Portainer container is running."""
        manager: PortainerDockerManager | None = hass.data.get(DOMAIN, {}).get(
            DATA_MANAGER
        )
        if manager is None:
            _LOGGER.error("Portainer manager is not available")
            return
        await manager.async_ensure_running()

    async def async_stop_container(_call: ServiceCall) -> None:
        """Stop the Portainer container."""
        manager: PortainerDockerManager | None = hass.data.get(DOMAIN, {}).get(
            DATA_MANAGER
        )
        if manager is None:
            _LOGGER.error("Portainer manager is not available")
            return
        await manager.async_stop()

    hass.services.async_register(DOMAIN, "restart_container", async_restart_container)
    hass.services.async_register(DOMAIN, "start_container", async_start_container)
    hass.services.async_register(DOMAIN, "stop_container", async_stop_container)
