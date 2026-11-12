"""Config flow for the Portainer integration."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from aiodocker.exceptions import DockerError

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_CONTAINER_NAME,
    CONF_DOCKER_HOST,
    CONF_IMAGE,
    CONF_PORT,
    CONF_SSL_PORT,
    CONF_STOP_ON_UNLOAD,
    CONF_UI_URL,
    CONF_VOLUME_NAME,
    DEFAULT_CONTAINER_NAME,
    DEFAULT_DOCKER_HOST,
    DEFAULT_IMAGE,
    DEFAULT_PORT,
    DEFAULT_SSL_PORT,
    DEFAULT_STOP_ON_UNLOAD,
    DEFAULT_VOLUME_NAME,
    DOMAIN,
)
from .docker_manager import async_validate_docker

_LOGGER = logging.getLogger(__name__)


def _default_ui_url(port: int) -> str:
    """Build a browser-reachable default Portainer URL for the host machine."""
    return f"http://homeassistant.local:{port}"


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DOCKER_HOST, default=DEFAULT_DOCKER_HOST): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
        ),
        vol.Required(CONF_CONTAINER_NAME, default=DEFAULT_CONTAINER_NAME): selector.TextSelector(),
        vol.Required(CONF_IMAGE, default=DEFAULT_IMAGE): selector.TextSelector(),
        vol.Required(CONF_PORT, default=DEFAULT_PORT): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=65535,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(CONF_SSL_PORT, default=DEFAULT_SSL_PORT): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=65535,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(CONF_VOLUME_NAME, default=DEFAULT_VOLUME_NAME): selector.TextSelector(),
        vol.Optional(CONF_UI_URL): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
        ),
        vol.Required(
            CONF_STOP_ON_UNLOAD, default=DEFAULT_STOP_ON_UNLOAD
        ): selector.BooleanSelector(),
    }
)


def _normalize_user_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Normalize and fill derived config values."""
    data = dict(user_input)
    data[CONF_PORT] = int(data[CONF_PORT])
    data[CONF_SSL_PORT] = int(data[CONF_SSL_PORT])
    data[CONF_DOCKER_HOST] = data[CONF_DOCKER_HOST].rstrip("/")
    data[CONF_CONTAINER_NAME] = data[CONF_CONTAINER_NAME].strip()
    data[CONF_IMAGE] = data[CONF_IMAGE].strip()
    data[CONF_VOLUME_NAME] = data[CONF_VOLUME_NAME].strip()

    ui_url = (data.get(CONF_UI_URL) or "").strip()
    if not ui_url:
        ui_url = _default_ui_url(data[CONF_PORT])
    parsed = urlparse(ui_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("invalid_ui_url")
    data[CONF_UI_URL] = ui_url.rstrip("/")
    data[CONF_NAME] = "Portainer"
    return data


class PortainerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Portainer."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                data = _normalize_user_input(user_input)
            except ValueError:
                errors["base"] = "invalid_ui_url"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()

                try:
                    version = await async_validate_docker(data[CONF_DOCKER_HOST])
                    _LOGGER.debug("Docker engine version %s", version)
                except DockerError:
                    _LOGGER.exception("Docker API error while validating host")
                    errors["base"] = "cannot_connect"
                except TimeoutError:
                    errors["base"] = "cannot_connect"
                except OSError:
                    _LOGGER.exception("Unable to reach Docker host")
                    errors["base"] = "cannot_connect"
                except Exception:  # noqa: BLE001 - surface unexpected Docker client failures
                    _LOGGER.exception("Unexpected error validating Docker host")
                    errors["base"] = "unknown"
                else:
                    return self.async_create_entry(title="Portainer", data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow handler."""
        return PortainerOptionsFlow()


class PortainerOptionsFlow(config_entries.OptionsFlow):
    """Handle Portainer options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the Portainer options."""
        errors: dict[str, str] = {}
        current = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            try:
                data = _normalize_user_input({**current, **user_input})
            except ValueError:
                errors["base"] = "invalid_ui_url"
            else:
                # Persist connection/runtime settings on the entry data so setup
                # always sees the latest values after a reload.
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        key: data[key]
                        for key in (
                            CONF_DOCKER_HOST,
                            CONF_CONTAINER_NAME,
                            CONF_IMAGE,
                            CONF_PORT,
                            CONF_SSL_PORT,
                            CONF_VOLUME_NAME,
                            CONF_UI_URL,
                            CONF_STOP_ON_UNLOAD,
                            CONF_NAME,
                        )
                    },
                )
                return self.async_create_entry(title="", data={})

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_UI_URL, default=current.get(CONF_UI_URL, _default_ui_url(DEFAULT_PORT))
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
                ),
                vol.Required(
                    CONF_PORT, default=current.get(CONF_PORT, DEFAULT_PORT)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=65535,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_SSL_PORT, default=current.get(CONF_SSL_PORT, DEFAULT_SSL_PORT)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=65535,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_IMAGE, default=current.get(CONF_IMAGE, DEFAULT_IMAGE)
                ): selector.TextSelector(),
                vol.Required(
                    CONF_STOP_ON_UNLOAD,
                    default=current.get(CONF_STOP_ON_UNLOAD, DEFAULT_STOP_ON_UNLOAD),
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
