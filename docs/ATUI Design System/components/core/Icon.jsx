import React from "react";

// Carbon icon registry — mirrors atui-components-stencil/src/icons/atui-icons.ts (ATUI_ICONS)
// plus common app icons. Values are @carbon/icons ES module paths (size 16).
export const ATUI_ICON_PATHS = {
  add: "add", arrow_left: "arrow--left", arrow_right: "arrow--right", arrow_up: "arrow--up",
  trend_up: "arrow--up-right", trend_down: "arrow--down-right", backspace: "delete", delete: "trash-can",
  cancel: "close--filled", caret_down: "caret--down", caret_up: "caret--up", checkmark: "checkmark",
  chevron_down: "chevron--down", chevron_left: "chevron--left", chevron_right: "chevron--right",
  close: "close", column: "voice-mode", copy: "copy", download: "download", edit: "edit",
  error: "warning--filled", filter_list: "arrange", first_page: "page--first", help: "help",
  info: "information", info_filled: "information--filled", last_page: "page--last",
  menu_expand: "side-panel--open", menu_collapse: "side-panel--close", overflow_menu: "overflow-menu--vertical",
  retry: "watson-health/rotate--360", schedule: "event--schedule", search: "ibm-watson--discovery",
  send: "send", stop: "stop--filled--alt", subtract: "subtract", success: "checkmark--filled",
  thumbs_down: "thumbs-down", thumbs_down_filled: "thumbs-down--filled", thumbs_up: "thumbs-up",
  thumbs_up_filled: "thumbs-up--filled", warning: "warning--alt--filled", edit_filters: "filter--edit",
  data_table: "data-table",
  // app icons (OneConnect-style navigation)
  home: "home", dashboard: "dashboard", settings: "settings", user: "user", user_multiple: "user--multiple",
  logout: "logout", notification: "notification", network: "network--3", router: "router", switch: "switcher",
  wifi: "wifi", location: "location", map: "map", events: "event", time: "time", filter: "filter",
  upgrade: "upgrade", view: "view", launch: "launch", renew: "renew", devices: "devices", folder: "folder",
  document: "document", calendar: "calendar", maximize: "maximize", building: "building", chat: "chat",
  light: "light", asleep: "asleep", security: "security", ai: "ai-generate", attachment: "attachment",
};

const cache = new Map();
const CDN = "https://cdn.jsdelivr.net/npm/@carbon/icons@11/es/";
const dynImport = new Function("u", "return import(u)");

function load(path) {
  if (!cache.has(path)) {
    cache.set(path, dynImport(CDN + path + "/16.js").then((m) => m.default).catch(() => null));
  }
  return cache.get(path);
}

function renderNode(node, i) {
  const { elem, attrs = {}, content } = node;
  const props = { key: i };
  for (const k in attrs) props[k === "fill-rule" ? "fillRule" : k === "clip-rule" ? "clipRule" : k === "class" ? "className" : k] = attrs[k];
  return React.createElement(elem, props, content ? content.map(renderNode) : undefined);
}

const SIZES = { xs: 24, sm: 48, md: 64, lg: 72 };

/** Carbon icon, rendered like <at-icon>: fill is currentColor, 16px default. */
export function Icon({ name, carbon, size = 16, color, style, className, title }) {
  const path = carbon || ATUI_ICON_PATHS[name] || name;
  const [desc, setDesc] = React.useState(null);
  React.useEffect(() => {
    let live = true;
    if (path) load(path).then((d) => live && setDesc(d));
    return () => { live = false; };
  }, [path]);
  const px = SIZES[size] || size;
  const box = { display: "inline-flex", flex: "none", width: px, height: px, color, fill: "currentColor", ...style };
  if (!desc) return <span className={className} style={box} aria-hidden="true"></span>;
  return (
    <span className={className} style={box} role={title ? "img" : undefined} aria-label={title} aria-hidden={title ? undefined : "true"}>
      <svg width={px} height={px} viewBox={desc.attrs.viewBox} fill="currentColor">{desc.content.map(renderNode)}</svg>
    </span>
  );
}
