"""Register the Portainer sidebar panel."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .const import (
    CONF_UI_URL,
    DATA_PANEL_REGISTERED,
    DOMAIN,
    PANEL_ICON,
    PANEL_MODULE_URL,
    PANEL_STATIC_URL,
    PANEL_TITLE,
    PANEL_URL_PATH,
    PANEL_WEBCOMPONENT,
)

_LOGGER = logging.getLogger(__name__)

DATA_STATIC_REGISTERED = "static_registered"


async def async_setup_panel(hass: HomeAssistant, ui_url: str) -> None:
    """Serve the panel module and register a sidebar entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})

    if not domain_data.get(DATA_STATIC_REGISTERED):
        panel_dir = Path(__file__).parent / "www"
        await hass.http.async_register_static_paths(
            [StaticPathConfig(PANEL_STATIC_URL, str(panel_dir), cache_headers=False)]
        )
        domain_data[DATA_STATIC_REGISTERED] = True

    if "panel_custom" not in hass.config.components:
        await async_setup_component(hass, "panel_custom", {})

    if domain_data.get(DATA_PANEL_REGISTERED):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)

    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_WEBCOMPONENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=PANEL_MODULE_URL,
        embed_iframe=True,
        require_admin=True,
        config={"url": ui_url},
    )
    domain_data[DATA_PANEL_REGISTERED] = True
    _LOGGER.info(
        "Registered Portainer sidebar panel at /%s -> %s", PANEL_URL_PATH, ui_url
    )


async def async_unload_panel(hass: HomeAssistant) -> None:
    """Remove the Portainer sidebar panel when the integration unloads."""
    domain_data = hass.data.get(DOMAIN, {})
    if not domain_data.get(DATA_PANEL_REGISTERED):
        return

    frontend.async_remove_panel(hass, PANEL_URL_PATH)
    domain_data[DATA_PANEL_REGISTERED] = False
    _LOGGER.info("Removed Portainer sidebar panel")


def panel_url_from_entry_data(data: dict) -> str:
    """Extract the configured Portainer UI URL."""
    return data[CONF_UI_URL]
