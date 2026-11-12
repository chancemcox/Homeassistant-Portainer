# Home Assistant Portainer

HACS-compatible custom integration that runs **Portainer CE** as a Docker container from Home Assistant and adds a **sidebar menu item** that opens the Portainer web UI.

## Features

- Config-flow setup from **Settings → Devices & services**
- Pulls and starts `portainer/portainer-ce` through the Docker Engine API (`aiodocker`)
- Persists Portainer data in a Docker volume (default `portainer_data`)
- Registers a left-sidebar **Portainer** panel that embeds the UI
- Status sensor for the managed container
- Services: `portainer.start_container`, `portainer.stop_container`, `portainer.restart_container`

## Requirements

Home Assistant must be able to reach a Docker engine. The common Container install pattern is:

```yaml
# docker-compose excerpt for Home Assistant
services:
  homeassistant:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

> Home Assistant OS / Supervised do **not** normally expose the Docker socket to custom integrations. Use Home Assistant Container (or another install with Docker socket access), or point **Docker host URL** at a remote engine that does.

Your browser must also be able to open the configured **Portainer UI URL** (the sidebar iframe loads that URL directly).

## HACS installation

1. HACS → Integrations → Custom repositories
2. Add this repository as type **Integration**
3. Install **Portainer**
4. Restart Home Assistant
5. Settings → Devices & services → Add integration → **Portainer**

## Manual installation

1. Copy `custom_components/portainer` into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Add the **Portainer** integration from the UI

## Configuration

| Option | Default | Description |
| --- | --- | --- |
| Docker host URL | `unix://var/run/docker.sock` | Docker Engine endpoint |
| Container name | `portainer` | Managed container name |
| Container image | `portainer/portainer-ce:latest` | Image to pull/run |
| HTTP port | `9000` | Host port → container `9000` |
| HTTPS port | `9443` | Host port → container `9443` |
| Data volume name | `portainer_data` | Persistent Portainer volume |
| Portainer UI URL | `http://homeassistant.local:9000` | URL opened by the sidebar panel |
| Stop on unload | `false` | Stop the container when the integration is removed |

On first start, complete Portainer’s own admin setup in the sidebar panel.

## File layout

```text
hacs.json
README.md
custom_components/portainer/
  __init__.py
  manifest.json
  const.py
  config_flow.py
  docker_manager.py
  panel.py
  sensor.py
  services.yaml
  strings.json
  translations/en.json
  www/portainer-panel.js
  brand/icon.png
  brand/logo.png
```

## Notes

- This integration manages Portainer as a Docker container. It is not a Home Assistant OS add-on package.
- Portainer is not financial/security advice tooling; treat Docker socket access as full host control and limit who can use the panel (`require_admin` is enabled).
