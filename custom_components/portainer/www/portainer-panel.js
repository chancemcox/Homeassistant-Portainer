class PortainerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  set hass(_hass) {
    // Home Assistant provides the hass object; unused for a pure iframe panel.
  }

  set panel(panel) {
    const url = panel && panel.config ? panel.config.url : "";
    this._render(url);
  }

  _render(url) {
    if (!this.shadowRoot) {
      return;
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          width: 100%;
          height: 100%;
          background: var(--primary-background-color);
        }
        .wrap {
          position: absolute;
          inset: 0;
          display: flex;
          flex-direction: column;
        }
        .missing {
          margin: auto;
          padding: 24px;
          max-width: 520px;
          text-align: center;
          color: var(--primary-text-color);
          font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
        }
        iframe {
          border: 0;
          width: 100%;
          height: 100%;
          background: var(--primary-background-color);
        }
      </style>
      <div class="wrap">
        ${
          url
            ? `<iframe
                 src="${url}"
                 title="Portainer"
                 allow="fullscreen"
                 referrerpolicy="no-referrer"
               ></iframe>`
            : `<div class="missing">
                 <h2>Portainer URL not configured</h2>
                 <p>Reconfigure the Portainer integration and set a browser-reachable UI URL.</p>
               </div>`
        }
      </div>
    `;
  }
}

customElements.define("portainer-panel", PortainerPanel);
