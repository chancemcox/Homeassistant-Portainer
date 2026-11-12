"""Constants for the Portainer integration."""

from typing import Final

DOMAIN: Final = "portainer"

CONF_CONTAINER_NAME: Final = "container_name"
CONF_DOCKER_HOST: Final = "docker_host"
CONF_IMAGE: Final = "image"
CONF_PORT: Final = "port"
CONF_SSL_PORT: Final = "ssl_port"
CONF_UI_URL: Final = "ui_url"
CONF_VOLUME_NAME: Final = "volume_name"
CONF_STOP_ON_UNLOAD: Final = "stop_on_unload"

DEFAULT_CONTAINER_NAME: Final = "portainer"
DEFAULT_DOCKER_HOST: Final = "unix://var/run/docker.sock"
DEFAULT_IMAGE: Final = "portainer/portainer-ce:latest"
DEFAULT_PORT: Final = 9000
DEFAULT_SSL_PORT: Final = 9443
DEFAULT_VOLUME_NAME: Final = "portainer_data"
DEFAULT_STOP_ON_UNLOAD: Final = False

PANEL_URL_PATH: Final = "portainer"
PANEL_ICON: Final = "mdi:docker"
PANEL_TITLE: Final = "Portainer"
PANEL_WEBCOMPONENT: Final = "portainer-panel"
PANEL_STATIC_URL: Final = f"/{DOMAIN}/static"
PANEL_MODULE_URL: Final = f"{PANEL_STATIC_URL}/portainer-panel.js"

DATA_MANAGER: Final = "manager"
DATA_PANEL_REGISTERED: Final = "panel_registered"
