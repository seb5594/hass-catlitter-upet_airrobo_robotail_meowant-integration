/*
 * Cat Litter Hub Lovelace cards: ubpet-litter-box-card and ubpet-cat-card.
 * Plain custom elements without a build step. Registered automatically by the integration.
 *
 * Entities are found through the device and the entity's translation key, so the cards keep working
 * when entities are renamed and in every language.
 */
const DOMAIN = "ubpet_cat_litter_hub";
const MODEL_BOX = "Litter box";
const MODEL_CAT = "Cat";

/* ---------- texts (only what Home Assistant itself cannot translate) ---------- */
const TEXTS = {
  en: {
    device: "Device", name: "Name (optional)", image: "Image URL (optional)", show_picture: "Show picture",
    sections: "Sections", chips: "Info chips", actions: "Actions", stats: "Statistics",
    sec_status: "Status", sec_presence: "Cat presence", sec_bin: "Waste bin", sec_chips: "Info chips",
    sec_actions: "Actions", sec_stats: "Statistics", pick_box: "Select a litter box device in the card settings.",
    pick_cat: "Select a cat device in the card settings.", confirm: "Run this action?",
  },
  de: {
    device: "Gerät", name: "Name (optional)", image: "Bild-URL (optional)", show_picture: "Bild anzeigen",
    sections: "Bereiche", chips: "Info-Chips", actions: "Aktionen", stats: "Statistiken",
    sec_status: "Status", sec_presence: "Anwesenheit der Katze", sec_bin: "Abfallbehälter", sec_chips: "Info-Chips",
    sec_actions: "Aktionen", sec_stats: "Statistiken", pick_box: "Wähle in den Karteneinstellungen ein Katzenklo.",
    pick_cat: "Wähle in den Karteneinstellungen eine Katze.", confirm: "Aktion ausführen?",
  },
  fr: {
    device: "Appareil", name: "Nom (facultatif)", image: "URL de l'image (facultatif)", show_picture: "Afficher l'image",
    sections: "Sections", chips: "Pastilles d'infos", actions: "Actions", stats: "Statistiques",
    sec_status: "État", sec_presence: "Présence du chat", sec_bin: "Bac à déchets", sec_chips: "Pastilles d'infos",
    sec_actions: "Actions", sec_stats: "Statistiques", pick_box: "Choisissez un bac dans les réglages de la carte.",
    pick_cat: "Choisissez un chat dans les réglages de la carte.", confirm: "Exécuter cette action ?",
  },
  es: {
    device: "Dispositivo", name: "Nombre (opcional)", image: "URL de la imagen (opcional)", show_picture: "Mostrar imagen",
    sections: "Secciones", chips: "Chips de información", actions: "Acciones", stats: "Estadísticas",
    sec_status: "Estado", sec_presence: "Presencia del gato", sec_bin: "Cubo de residuos", sec_chips: "Chips de información",
    sec_actions: "Acciones", sec_stats: "Estadísticas", pick_box: "Elige un arenero en los ajustes de la tarjeta.",
    pick_cat: "Elige un gato en los ajustes de la tarjeta.", confirm: "¿Ejecutar esta acción?",
  },
  it: {
    device: "Dispositivo", name: "Nome (facoltativo)", image: "URL dell'immagine (facoltativo)", show_picture: "Mostra immagine",
    sections: "Sezioni", chips: "Chip informativi", actions: "Azioni", stats: "Statistiche",
    sec_status: "Stato", sec_presence: "Presenza del gatto", sec_bin: "Contenitore rifiuti", sec_chips: "Chip informativi",
    sec_actions: "Azioni", sec_stats: "Statistiche", pick_box: "Scegli una lettiera nelle impostazioni della scheda.",
    pick_cat: "Scegli un gatto nelle impostazioni della scheda.", confirm: "Eseguire questa azione?",
  },
  nl: {
    device: "Apparaat", name: "Naam (optioneel)", image: "Afbeeldings-URL (optioneel)", show_picture: "Afbeelding tonen",
    sections: "Secties", chips: "Info-chips", actions: "Acties", stats: "Statistieken",
    sec_status: "Status", sec_presence: "Aanwezigheid van de kat", sec_bin: "Afvalbak", sec_chips: "Info-chips",
    sec_actions: "Acties", sec_stats: "Statistieken", pick_box: "Kies een kattenbak in de kaartinstellingen.",
    pick_cat: "Kies een kat in de kaartinstellingen.", confirm: "Deze actie uitvoeren?",
  },
  pl: {
    device: "Urządzenie", name: "Nazwa (opcjonalnie)", image: "URL obrazu (opcjonalnie)", show_picture: "Pokaż obraz",
    sections: "Sekcje", chips: "Znaczniki informacji", actions: "Akcje", stats: "Statystyki",
    sec_status: "Stan", sec_presence: "Obecność kota", sec_bin: "Pojemnik na odpady", sec_chips: "Znaczniki informacji",
    sec_actions: "Akcje", sec_stats: "Statystyki", pick_box: "Wybierz kuwetę w ustawieniach karty.",
    pick_cat: "Wybierz kota w ustawieniach karty.", confirm: "Wykonać tę akcję?",
  },
  pt: {
    device: "Dispositivo", name: "Nome (opcional)", image: "URL da imagem (opcional)", show_picture: "Mostrar imagem",
    sections: "Secções", chips: "Chips de informação", actions: "Ações", stats: "Estatísticas",
    sec_status: "Estado", sec_presence: "Presença do gato", sec_bin: "Depósito de resíduos", sec_chips: "Chips de informação",
    sec_actions: "Ações", sec_stats: "Estatísticas", pick_box: "Escolha uma caixa de areia nas definições do cartão.",
    pick_cat: "Escolha um gato nas definições do cartão.", confirm: "Executar esta ação?",
  },
};

function text(hass, key) {
  const language = String(hass?.locale?.language || hass?.language || "en").toLowerCase();
  return (TEXTS[language] || TEXTS[language.split("-")[0]] || TEXTS.en)[key] ?? TEXTS.en[key] ?? key;
}

/* ---------- entity lookup ---------- */
const indexCache = new WeakMap();

/** device_id -> { "<domain>:<translation_key>": entity_id } for this integration only. */
function entityIndex(hass) {
  const registry = hass.entities || {};
  let index = indexCache.get(registry);
  if (!index) {
    index = new Map();
    for (const entry of Object.values(registry)) {
      if (entry.platform !== DOMAIN || !entry.device_id || !entry.translation_key) continue;
      const domain = entry.entity_id.split(".")[0];
      if (!index.has(entry.device_id)) index.set(entry.device_id, {});
      index.get(entry.device_id)[`${domain}:${entry.translation_key}`] = entry.entity_id;
    }
    indexCache.set(registry, index);
  }
  return index;
}

/** Everything a card needs to read one device. */
function context(hass, config) {
  // `entity` (any entity of the device) is an easier alternative to the device ID.
  const deviceId = config.device_id || (hass.entities || {})[config.entity]?.device_id;
  const ids = entityIndex(hass).get(deviceId) || {};
  const device = (hass.devices || {})[deviceId];
  const deviceName = device?.name_by_user || device?.name || "";
  const entity = (domain, key) => {
    const id = ids[`${domain}:${key}`];
    return id ? hass.states[id] : undefined;
  };
  // Entity names include the device name; the card only needs the part that tells entities apart.
  const label = (stateObj) => {
    const full = stateObj?.attributes?.friendly_name || "";
    return deviceName && full.startsWith(deviceName) ? full.slice(deviceName.length).trim() || full : full;
  };
  return { hass, config, ids, device, deviceName, entity, label };
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

const UNAVAILABLE = new Set(["unavailable", "unknown"]);
const isUsable = (s) => s && !UNAVAILABLE.has(s.state);

function formatTimestamp(hass, iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return String(iso);
  const language = hass.locale?.language || hass.language;
  const useServerZone = hass.locale?.time_zone === "server" && hass.config?.time_zone;
  const sameDay = date.toDateString() === new Date().toDateString();
  const options = sameDay
    ? { hour: "2-digit", minute: "2-digit" }
    : { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" };
  try {
    return date.toLocaleString(language, useServerZone ? { ...options, timeZone: hass.config.time_zone } : options);
  } catch (_err) {
    return date.toLocaleString(language, options);
  }
}

function formatState(hass, stateObj) {
  if (!stateObj) return "–";
  if (UNAVAILABLE.has(stateObj.state)) return hass.formatEntityState ? hass.formatEntityState(stateObj) : stateObj.state;
  if (stateObj.attributes.device_class === "timestamp") return formatTimestamp(hass, stateObj.state);
  if (hass.formatEntityState) return hass.formatEntityState(stateObj);
  return `${stateObj.state}${stateObj.attributes.unit_of_measurement ? ` ${stateObj.attributes.unit_of_measurement}` : ""}`;
}

/* ---------- shared base ---------- */
const STYLE = `<style>
  :host { display: block; }
  ha-card { padding: 16px; overflow: hidden; }
  .title { font-size: 1.25rem; font-weight: 500; text-align: center; margin: 0 0 12px; color: var(--primary-text-color); }
  .hint { padding: 16px; text-align: center; color: var(--secondary-text-color); }
  .block { display: flex; flex-direction: column; align-items: center; gap: 4px; margin: 10px 0; text-align: center; }
  .block .cap { font-size: .8rem; color: var(--secondary-text-color); }
  .block .big { font-size: 1.05rem; color: var(--primary-text-color); }
  .hero { display: flex; align-items: center; justify-content: center; gap: 16px; }
  .hero img { max-width: 40%; max-height: 120px; object-fit: contain; border-radius: 12px; }
  .status ha-icon { --mdc-icon-size: 34px; }
  .spin ha-icon { animation: spin 2s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .ok { color: var(--success-color, #43a047); } .warn { color: var(--warning-color, #ffa600); }
  .bad { color: var(--error-color, #db4437); } .info { color: var(--info-color, #2196f3); }
  .bar { width: 70%; height: 8px; border-radius: 4px; background: var(--divider-color); overflow: hidden; }
  .bar > div { height: 100%; background: var(--primary-color); } .bar.warn > div { background: var(--warning-color, #ffa600); }
  .bar.bad > div { background: var(--error-color, #db4437); }
  .chips, .actions { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin: 12px 0; }
  .chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 16px; cursor: pointer;
    background: var(--secondary-background-color); font-size: .85rem; color: var(--primary-text-color); }
  .chip ha-icon { --mdc-icon-size: 18px; }
  .actions button { all: unset; box-sizing: border-box; display: flex; flex-direction: column; align-items: center; gap: 4px;
    min-width: 76px; padding: 8px; border-radius: 12px; cursor: pointer; text-align: center; font-size: .8rem;
    color: var(--primary-text-color); }
  .actions button:hover:not([disabled]) { background: var(--secondary-background-color); }
  .actions button[disabled] { opacity: .4; cursor: default; }
  .actions button ha-icon { --mdc-icon-size: 28px; color: var(--primary-color); }
  .stats { margin-top: 8px; border-top: 1px solid var(--divider-color); padding-top: 8px; }
  .row { display: flex; align-items: center; gap: 10px; padding: 6px 0; cursor: pointer; }
  .row ha-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); }
  .row .lbl { flex: 1; color: var(--secondary-text-color); } .row .val { color: var(--primary-text-color); font-weight: 500; text-align: right; }
  .split ha-icon { --mdc-icon-size: 16px; vertical-align: middle; }
  .cat-head { display: flex; align-items: center; gap: 14px; margin-bottom: 8px; }
  .cat-head img { width: 64px; height: 64px; border-radius: 50%; object-fit: cover; background: var(--secondary-background-color); }
  .cat-head .nm { font-size: 1.25rem; font-weight: 500; } .cat-head .wt { color: var(--secondary-text-color); }
  :host(.compact) .row { padding: 3px 0; }
</style>`;

class UbpetCardBase extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._html = "";
    this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
  }

  setConfig(config) {
    this._config = { ...this.constructor.defaults, ...config };
    this._html = "";
    this._draw();
  }

  set hass(hass) {
    this._hass = hass;
    this._draw();
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  _draw() {
    if (!this._config || !this._hass) return;
    const ctx = context(this._hass, this._config);
    const body = ctx.device ? this._render(ctx) : `<div class="hint">${esc(text(this._hass, this.constructor.pick))}</div>`;
    const html = `${STYLE}<ha-card>${body}</ha-card>`;
    if (html !== this._html) {
      this._html = html;
      this.shadowRoot.innerHTML = html;
    }
  }

  _onClick(event) {
    const target = event.target.closest("[data-press],[data-more]");
    if (!target || !this._hass) return;
    if (target.dataset.press) {
      if (target.hasAttribute("disabled")) return;
      if (target.dataset.confirm && !window.confirm(text(this._hass, "confirm"))) return;
      this._hass.callService("button", "press", { entity_id: target.dataset.press });
    } else {
      this.dispatchEvent(
        new CustomEvent("hass-more-info", { detail: { entityId: target.dataset.more }, bubbles: true, composed: true }),
      );
    }
  }

  /** One "label  value" line; the whole line opens the entity's more-info dialog. */
  _row(ctx, stateObj, icon, valueHtml) {
    if (!stateObj) return "";
    const value = valueHtml ?? esc(formatState(ctx.hass, stateObj));
    return `<div class="row" data-more="${esc(stateObj.entity_id)}"><ha-icon icon="${esc(icon)}"></ha-icon>
      <span class="lbl">${esc(ctx.label(stateObj))}</span><span class="val">${value}</span></div>`;
  }
}

/* ---------- litter box card ---------- */
const BOX_STATUS_ICON = { running: "mdi:autorenew", standby: "mdi:check-circle-outline", paused: "mdi:pause-circle-outline" };

const BOX_CHIPS = {
  online: (c) => {
    const s = c.entity("binary_sensor", "online");
    return s && { id: s.entity_id, icon: s.state === "on" ? "mdi:wifi" : "mdi:wifi-off", cls: s.state === "on" ? "ok" : "bad", text: formatState(c.hass, s) };
  },
  deodorant: (c) => {
    const s = c.entity("sensor", "deodorant_remaining_days");
    const expired = c.entity("binary_sensor", "deodorant_expired")?.state === "on";
    return s && { id: s.entity_id, icon: "mdi:air-filter", cls: expired || Number(s.state) <= 3 ? "warn" : "", text: formatState(c.hass, s) };
  },
  child_lock: (c) => {
    const s = c.entity("switch", "child_lock") || c.entity("binary_sensor", "control_board_switch");
    return s && { id: s.entity_id, icon: s.state === "on" ? "mdi:lock" : "mdi:lock-open-variant", cls: "", text: formatState(c.hass, s) };
  },
  auto_clean_delay: (c) => {
    const s = c.entity("sensor", "auto_clean_delay_current");
    return s && { id: s.entity_id, icon: "mdi:timer-sand", cls: "", text: formatState(c.hass, s) };
  },
  problems: (c) => {
    const keys = ["cover_open", "drum_stuck", "drum_not_in_place", "scale_fault", "camera_fault"];
    const active = keys.map((k) => c.entity("binary_sensor", k)).find((s) => s?.state === "on");
    return active && { id: active.entity_id, icon: "mdi:alert", cls: "bad", text: c.label(active) };
  },
};

const BOX_ACTIONS = {
  clean: ["mqtt_start_clean_up", "mdi:broom"],
  pause_clean: ["mqtt_pause_clean_up", "mdi:pause"],
  resume_clean: ["mqtt_resume_clean_up", "mdi:play"],
  flatten: ["mqtt_start_flatten", "mdi:waves"],
  pause_flatten: ["mqtt_pause_flatten", "mdi:pause"],
  resume_flatten: ["mqtt_resume_flatten", "mdi:play"],
  rake_up: ["mqtt_start_rise", "mdi:arrow-up-bold"],
  rake_down: ["mqtt_start_drop", "mdi:arrow-down-bold"],
  reset_bin: ["reset_waste_bin", "mdi:delete-restore", true],
  reset_deodorant: ["reset_deodorant", "mdi:air-filter", true],
  request_state: ["mqtt_request_state", "mdi:refresh"],
  rest_request: ["rest_request", "mdi:cloud-refresh"],
};

const BOX_STATS = {
  visits_today: ["sensor", "visits_today", "mdi:counter"],
  cleans_today: ["sensor", "cleans_today", "mdi:broom"],
  last_clean: ["sensor", "last_clean", "mdi:broom"],
  last_visit: ["sensor", "last_visit", "mdi:cat"],
  last_used_by: ["sensor", "last_used_by", "mdi:cat"],
  cleans_since_bin_reset: ["sensor", "cleans_since_bin_reset", "mdi:delete-restore"],
  remaining_bin_uses: ["sensor", "remaining_bin_uses", "mdi:delete-clock"],
  scheduled_cleans: ["sensor", "scheduled_cleans", "mdi:calendar-clock"],
  firmware_version: ["sensor", "firmware_version", "mdi:chip"],
};

const BOX_SECTIONS = ["status", "presence", "bin", "chips", "actions", "stats"];

class UbpetLitterBoxCard extends UbpetCardBase {
  static pick = "pick_box";
  static defaults = {
    sections: ["status", "presence", "bin", "chips", "actions"],
    chips: ["online", "deodorant", "child_lock", "auto_clean_delay", "problems"],
    actions: ["clean", "flatten", "reset_bin", "request_state"],
    stats: [],
  };

  static getConfigElement() {
    return document.createElement("ubpet-litter-box-card-editor");
  }

  static getStubConfig(hass) {
    return { device_id: firstDevice(hass, MODEL_BOX) };
  }

  _render(ctx) {
    const cfg = this._config;
    const sections = (cfg.sections || []).filter((s) => BOX_SECTIONS.includes(s));
    const title = cfg.name || ctx.deviceName;
    const image = cfg.image ? `<img src="${esc(cfg.image)}" alt="">` : "";
    const body = sections.map((s) => this[`_${s}`](ctx)).join("");
    return `${title ? `<div class="title">${esc(title)}</div>` : ""}${image ? `<div class="hero">${image}</div>` : ""}${body}`;
  }

  _status(ctx) {
    const s = ctx.entity("sensor", "box_status");
    if (!s) return "";
    const icon = BOX_STATUS_ICON[s.state] || "mdi:help-circle-outline";
    const cls = s.state === "running" ? "info spin" : s.state === "paused" ? "warn" : isUsable(s) ? "ok" : "";
    return `<div class="block status ${cls}" data-more="${esc(s.entity_id)}"><span class="cap">${esc(ctx.label(s))}</span>
      <ha-icon icon="${icon}"></ha-icon><span class="big">${esc(formatState(ctx.hass, s))}</span></div>`;
  }

  _presence(ctx) {
    const s = ctx.entity("sensor", "mqtt_pet_position");
    const flag = ctx.entity("binary_sensor", "cat_inside");
    const source = s || flag;
    if (!source) return "";
    const inside = s ? s.state === "inside" : flag.state === "on";
    return `<div class="block" data-more="${esc(source.entity_id)}"><span class="cap">${esc(ctx.label(flag || source))}</span>
      <span class="big ${inside ? "info" : ""}"><ha-icon icon="mdi:cat"></ha-icon> ${esc(formatState(ctx.hass, source))}</span></div>`;
  }

  _bin(ctx) {
    const level = ctx.entity("sensor", "waste_bin_level");
    if (!level) return "";
    const value = Number(level.state);
    const full = ctx.entity("binary_sensor", "waste_bin_full")?.state === "on";
    const cls = full ? "bad" : value >= 80 ? "warn" : "";
    const width = Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : 0;
    const remaining = ctx.entity("sensor", "remaining_bin_uses");
    return `<div class="block" data-more="${esc(level.entity_id)}"><span class="cap">${esc(ctx.label(level))}</span>
      <span class="big ${cls}"><ha-icon icon="mdi:delete-outline"></ha-icon> ${esc(formatState(ctx.hass, level))}${full ? ' <ha-icon icon="mdi:alert"></ha-icon>' : ""}</span>
      <div class="bar ${cls}"><div style="width:${width}%"></div></div>
      ${isUsable(remaining) ? `<span class="cap">${esc(ctx.label(remaining))}: ${esc(formatState(ctx.hass, remaining))}</span>` : ""}</div>`;
  }

  _chips(ctx) {
    const chips = (this._config.chips || []).map((k) => BOX_CHIPS[k]?.(ctx)).filter(Boolean);
    if (!chips.length) return "";
    return `<div class="chips">${chips
      .map((c) => `<span class="chip ${c.cls}" data-more="${esc(c.id)}"><ha-icon icon="${c.icon}"></ha-icon>${esc(c.text)}</span>`)
      .join("")}</div>`;
  }

  _actions(ctx) {
    const buttons = (this._config.actions || [])
      .map((k) => {
        const [key, icon, confirm] = BOX_ACTIONS[k] || [];
        const s = key && ctx.entity("button", key);
        if (!s) return "";
        const off = s.state === "unavailable" ? " disabled" : ""; // buttons idle at "unknown"
        return `<button data-press="${esc(s.entity_id)}"${confirm ? ' data-confirm="1"' : ""}${off}>
          <ha-icon icon="${icon}"></ha-icon><span>${esc(ctx.label(s))}</span></button>`;
      })
      .join("");
    return buttons ? `<div class="actions">${buttons}</div>` : "";
  }

  _stats(ctx) {
    const rows = (this._config.stats || [])
      .map((k) => {
        const [domain, key, icon] = BOX_STATS[k] || [];
        return key ? this._row(ctx, ctx.entity(domain, key), icon) : "";
      })
      .join("");
    return rows ? `<div class="stats">${rows}</div>` : "";
  }
}

/* ---------- cat card ---------- */
const CAT_STATS = {
  cat_last_visit_duration: ["sensor", "cat_last_visit_duration", "mdi:timer-outline"],
  cat_visits_24h: ["sensor", "cat_visits_24h", "mdi:counter"],
  visits_split: ["sensor", "cat_visits_24h", "mdi:toilet"],
  cat_visits_today: ["sensor", "cat_visits_today", "mdi:counter"],
  cat_last_visit: ["sensor", "cat_last_visit", "mdi:cat"],
  cat_last_poo: ["sensor", "cat_last_poo", "mdi:emoticon-poop"],
  cat_last_pee: ["sensor", "cat_last_pee", "mdi:water"],
  cat_pee_visits_24h: ["sensor", "cat_pee_visits_24h", "mdi:water"],
  cat_poo_visits_24h: ["sensor", "cat_poo_visits_24h", "mdi:emoticon-poop"],
  cat_duration_24h: ["sensor", "cat_duration_24h", "mdi:timer-sand"],
  cat_average_duration_24h: ["sensor", "cat_average_duration_24h", "mdi:timer-outline"],
  cat_maximum_duration_24h: ["sensor", "cat_maximum_duration_24h", "mdi:timer-alert-outline"],
  cat_last_visit_weight: ["sensor", "cat_last_visit_weight", "mdi:scale"],
  cat_weight_change: ["sensor", "cat_weight_change", "mdi:scale"],
};

class UbpetCatCard extends UbpetCardBase {
  static pick = "pick_cat";
  static defaults = {
    show_picture: true,
    stats: ["cat_last_visit_duration", "visits_split", "cat_last_poo", "cat_last_pee"],
  };

  static getConfigElement() {
    return document.createElement("ubpet-cat-card-editor");
  }

  static getStubConfig(hass) {
    return { device_id: firstDevice(hass, MODEL_CAT) };
  }

  getCardSize() {
    return 4;
  }

  _render(ctx) {
    const cfg = this._config;
    const weight = ctx.entity("sensor", "cat_weight");
    const picture = cfg.image || weight?.attributes?.picture || ctx.entity("sensor", "cat_visits_24h")?.attributes?.picture;
    const head = `<div class="cat-head">${cfg.show_picture && picture ? `<img src="${esc(picture)}" alt="">` : ""}
      <div><div class="nm">${esc(cfg.name || ctx.deviceName)}</div>
      ${isUsable(weight) ? `<div class="wt" data-more="${esc(weight.entity_id)}">${esc(formatState(ctx.hass, weight))}</div>` : ""}</div></div>`;
    const rows = (cfg.stats || []).map((k) => this._stat(ctx, k)).join("");
    return `${head}${rows ? `<div class="stats">${rows}</div>` : ""}`;
  }

  _stat(ctx, key) {
    const [domain, entityKey, icon] = CAT_STATS[key] || [];
    const s = entityKey && ctx.entity(domain, entityKey);
    if (!s) return "";
    if (key !== "visits_split") return this._row(ctx, s, icon);
    const pee = ctx.entity("sensor", "cat_pee_visits_24h");
    const poo = ctx.entity("sensor", "cat_poo_visits_24h");
    const split = [pee && `<ha-icon icon="mdi:water"></ha-icon> ${esc(pee.state)}`, poo && `<ha-icon icon="mdi:emoticon-poop"></ha-icon> ${esc(poo.state)}`]
      .filter(Boolean)
      .join(" | ");
    return this._row(ctx, s, icon, `${esc(s.state)}${split ? ` <span class="split">(${split})</span>` : ""}`);
  }
}

/* ---------- editors ---------- */
function firstDevice(hass, model) {
  return Object.values(hass.devices || {}).find((d) => d.model === model && hasOurEntities(hass, d.id))?.id || "";
}

function hasOurEntities(hass, deviceId) {
  return entityIndex(hass).has(deviceId);
}

class UbpetEditorBase extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._draw();
  }

  set hass(hass) {
    this._hass = hass;
    this._draw();
  }

  /** Option list with entity names in the user's language, taken from the selected device. */
  _options(map, domainOf) {
    const ctx = context(this._hass, { device_id: this._config.device_id });
    return Object.keys(map).map((key) => {
      const [domain, entityKey] = domainOf(key);
      const stateObj = ctx.entity(domain, entityKey);
      return { value: key, label: stateObj ? ctx.label(stateObj) : key.replace(/_/g, " ") };
    });
  }

  _draw() {
    if (!this._hass || !this._config) return;
    const key = `${this._config.device_id}|${this._hass.language}`;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (event) => {
        event.stopPropagation();
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: event.detail.value }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    if (key !== this._schemaKey) {
      this._schemaKey = key;
      this._form.schema = this._schema();
      this._form.computeLabel = (field) => text(this._hass, field.name);
    }
    this._form.hass = this._hass;
    this._form.data = { ...this.constructor.cardClass.defaults, ...this._config };
  }

  _select(name, options) {
    return { name, selector: { select: { multiple: true, reorder: true, mode: "list", options } } };
  }

  _deviceField(model) {
    return { name: "device_id", selector: { device: { filter: [{ integration: DOMAIN, model }] } } };
  }
}

class UbpetLitterBoxCardEditor extends UbpetEditorBase {
  static cardClass = UbpetLitterBoxCard;

  _schema() {
    const sections = BOX_SECTIONS.map((s) => ({ value: s, label: text(this._hass, `sec_${s}`) }));
    return [
      this._deviceField(MODEL_BOX),
      { name: "name", selector: { text: {} } },
      { name: "image", selector: { text: {} } },
      this._select("sections", sections),
      this._select("chips", this._chipOptions()),
      this._select("actions", this._options(BOX_ACTIONS, (k) => ["button", BOX_ACTIONS[k][0]])),
      this._select("stats", this._options(BOX_STATS, (k) => [BOX_STATS[k][0], BOX_STATS[k][1]])),
    ];
  }

  _chipOptions() {
    const ctx = context(this._hass, { device_id: this._config.device_id });
    const source = {
      online: ["binary_sensor", "online"], deodorant: ["sensor", "deodorant_remaining_days"],
      child_lock: ["switch", "child_lock"], auto_clean_delay: ["sensor", "auto_clean_delay_current"],
      problems: ["binary_sensor", "cover_open"],
    };
    return Object.entries(source).map(([value, [domain, key]]) => {
      const stateObj = ctx.entity(domain, key);
      return { value, label: stateObj ? ctx.label(stateObj) : value.replace(/_/g, " ") };
    });
  }
}

class UbpetCatCardEditor extends UbpetEditorBase {
  static cardClass = UbpetCatCard;

  _schema() {
    return [
      this._deviceField(MODEL_CAT),
      { name: "name", selector: { text: {} } },
      { name: "image", selector: { text: {} } },
      { name: "show_picture", selector: { boolean: {} } },
      this._select("stats", this._options(CAT_STATS, (k) => [CAT_STATS[k][0], CAT_STATS[k][1]])),
    ];
  }
}

/* ---------- registration ---------- */
const ELEMENTS = {
  "ubpet-litter-box-card": UbpetLitterBoxCard,
  "ubpet-cat-card": UbpetCatCard,
  "ubpet-litter-box-card-editor": UbpetLitterBoxCardEditor,
  "ubpet-cat-card-editor": UbpetCatCardEditor,
};
for (const [name, element] of Object.entries(ELEMENTS)) {
  if (!customElements.get(name)) customElements.define(name, element);
}

window.customCards = window.customCards || [];
window.customCards.push(
  {
    type: "ubpet-litter-box-card",
    name: "Cat Litter Hub – Litter box",
    description: "Status, waste bin, info chips and actions of one smart litter box.",
    documentationURL: "https://github.com/seb5594/hass-ubpet_cat_litter_hub-integration",
  },
  {
    type: "ubpet-cat-card",
    name: "Cat Litter Hub – Cat",
    description: "Weight and visit statistics of one cat, with freely selectable values.",
    documentationURL: "https://github.com/seb5594/hass-ubpet_cat_litter_hub-integration",
  },
);
