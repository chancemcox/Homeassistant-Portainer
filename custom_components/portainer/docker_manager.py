"""Manage the Portainer Docker container lifecycle."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiodocker
from aiodocker.exceptions import DockerError

from homeassistant.core import HomeAssistant

from .const import (
    CONF_CONTAINER_NAME,
    CONF_DOCKER_HOST,
    CONF_IMAGE,
    CONF_PORT,
    CONF_SSL_PORT,
    CONF_VOLUME_NAME,
)

_LOGGER = logging.getLogger(__name__)


def _split_image(image: str) -> tuple[str, str | None]:
    """Split an image reference into repository and tag."""
    # Digest references keep the full string as fromImage.
    if "@" in image:
        return image, None
    if image.startswith("sha256:"):
        return image, None

    repo = image
    tag: str | None = None
    if ":" in image.rsplit("/", 1)[-1]:
        repo, tag = image.rsplit(":", 1)
    return repo, tag


class PortainerDockerManager:
    """Pull, create, start, and inspect the Portainer container."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the manager from config-entry data."""
        self.hass = hass
        self.container_name: str = config[CONF_CONTAINER_NAME]
        self.docker_host: str = config[CONF_DOCKER_HOST]
        self.image: str = config[CONF_IMAGE]
        self.port: int = int(config[CONF_PORT])
        self.ssl_port: int = int(config[CONF_SSL_PORT])
        self.volume_name: str = config[CONF_VOLUME_NAME]
        self._docker: aiodocker.Docker | None = None

    async def async_connect(self) -> None:
        """Open a connection to the Docker engine."""
        self._docker = aiodocker.Docker(url=self.docker_host)
        version = await self._docker.version()
        _LOGGER.info(
            "Connected to Docker %s at %s",
            version.get("Version", "unknown"),
            self.docker_host,
        )

    async def async_close(self) -> None:
        """Close the Docker client."""
        if self._docker is not None:
            await self._docker.close()
            self._docker = None

    def _require_docker(self) -> aiodocker.Docker:
        """Return the Docker client or raise if disconnected."""
        if self._docker is None:
            raise RuntimeError("Docker client is not connected")
        return self._docker

    async def async_ensure_running(self) -> dict[str, Any]:
        """Ensure Portainer image/volume/container exist and are running."""
        docker = self._require_docker()

        await self._async_ensure_image(docker)
        await self._async_ensure_volume(docker)

        container = await docker.containers.create_or_replace(
            name=self.container_name,
            config=self._container_config(),
        )

        info = await container.show()
        if info.get("State", {}).get("Status") != "running":
            _LOGGER.info("Starting Portainer container '%s'", self.container_name)
            await container.start()
            info = await container.show()

        _LOGGER.info(
            "Portainer container '%s' is %s",
            self.container_name,
            info.get("State", {}).get("Status"),
        )
        return info

    async def async_stop(self) -> None:
        """Stop the Portainer container if it is running."""
        docker = self._require_docker()
        try:
            container = await docker.containers.get(self.container_name)
        except DockerError as err:
            if err.status == 404:
                return
            raise

        info = await container.show()
        if info.get("State", {}).get("Status") == "running":
            _LOGGER.info("Stopping Portainer container '%s'", self.container_name)
            await container.stop()

    async def async_status(self) -> dict[str, Any] | None:
        """Return container inspect data, or None if missing."""
        docker = self._require_docker()
        try:
            container = await docker.containers.get(self.container_name)
        except DockerError as err:
            if err.status == 404:
                return None
            raise
        return await container.show()

    async def _async_ensure_image(self, docker: aiodocker.Docker) -> None:
        """Pull the Portainer image if it is not present locally."""
        try:
            await docker.images.inspect(self.image)
            _LOGGER.debug("Image %s already present", self.image)
            return
        except DockerError as err:
            if err.status != 404:
                raise

        repo, tag = _split_image(self.image)
        _LOGGER.info("Pulling Portainer image %s", self.image)
        result = docker.images.pull(repo, tag=tag)
        # aiodocker returns a coroutine or async generator depending on stream mode.
        if hasattr(result, "__aiter__"):
            async for _event in result:
                pass
        else:
            await result

    async def _async_ensure_volume(self, docker: aiodocker.Docker) -> None:
        """Create the persistent Portainer data volume if needed."""
        try:
            await docker.volumes.get(self.volume_name)
            return
        except DockerError as err:
            if err.status != 404:
                raise

        _LOGGER.info("Creating Docker volume '%s'", self.volume_name)
        await docker.volumes.create({"Name": self.volume_name})

    def _container_config(self) -> dict[str, Any]:
        """Build the Docker container create payload for Portainer CE."""
        return {
            "Image": self.image,
            "ExposedPorts": {
                "9000/tcp": {},
                "9443/tcp": {},
            },
            "HostConfig": {
                "Binds": [
                    "/var/run/docker.sock:/var/run/docker.sock",
                    f"{self.volume_name}:/data",
                ],
                "PortBindings": {
                    "9000/tcp": [{"HostPort": str(self.port)}],
                    "9443/tcp": [{"HostPort": str(self.ssl_port)}],
                },
                "RestartPolicy": {"Name": "unless-stopped"},
            },
            "Labels": {
                "managed_by": "homeassistant.portainer",
            },
        }


async def async_validate_docker(docker_host: str) -> str:
    """Validate Docker connectivity and return the engine version string."""
    docker = aiodocker.Docker(url=docker_host)
    try:
        version = await asyncio.wait_for(docker.version(), timeout=10)
    finally:
        await docker.close()
    return version.get("Version", "unknown")
