import React from "react";
import { Icon } from "../core/Icon.jsx";

const hoverBg = "color-mix(in srgb, var(--token-surface-overlay) 10%, transparent)";

/** at-menu-item — row inside a Menu. */
export function MenuItem({ label, icon, icon_after, is_active, disabled, onClick, children }) {
  const [h, setH] = React.useState(false);
  return (
    <div role="menuitem" tabIndex={0} onClick={(e) => !disabled && onClick && onClick(e)} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{ display: "flex", alignItems: "center", gap: 4, width: "100%", padding: "4px 8px", boxSizing: "border-box", borderRadius: "var(--token-menu-item-radius)", cursor: "pointer", overflow: "hidden", textAlign: "left",
        color: is_active ? "var(--token-state-active-accent)" : undefined, background: is_active ? "color-mix(in srgb, var(--token-state-active-accent) 10%, transparent)" : h ? hoverBg : "transparent",
        transition: "background-color 150ms ease-in-out", ...(disabled ? { pointerEvents: "none", opacity: 0.3, filter: "grayscale(1)" } : null) }}>
      <div style={{ display: "flex", flex: 1, minWidth: 0, alignItems: "center", gap: 8 }}>
        {icon && <Icon name={icon} />}
        {label && <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: "var(--token-font-size-body)", lineHeight: "var(--token-line-height-base)" }}>{label}</span>}
        {children}
      </div>
      {icon_after && <Icon name={icon_after} />}
    </div>
  );
}

/** at-menu — popover anchored to a trigger. items: [{label, icon, onClick, is_active, disabled}] or children. */
export function Menu({ trigger, items, children, position = "bottom", align = "start", width, open: openProp, onOpenChange, autoclose = true }) {
  const [open, setOpen] = React.useState(!!openProp);
  const ref = React.useRef();
  React.useEffect(() => { if (openProp !== undefined) setOpen(openProp); }, [openProp]);
  React.useEffect(() => {
    if (!open) return;
    const off = (e) => { if (ref.current && !ref.current.contains(e.target)) set(false); };
    document.addEventListener("mousedown", off);
    return () => document.removeEventListener("mousedown", off);
  }, [open]);
  const set = (v) => { setOpen(v); onOpenChange && onOpenChange(v); };
  const pos = position === "top" ? { bottom: "calc(100% + 4px)" } : { top: "calc(100% + 4px)" };
  return (
    <div ref={ref} style={{ position: "relative", display: "inline-flex" }}>
      <div onClick={() => set(!open)} style={{ display: "inline-flex" }}>{trigger}</div>
      {open && (
        <div role="menu" onClick={() => autoclose && set(false)}
          style={{ position: "absolute", ...pos, [align === "end" ? "right" : "left"]: 0, zIndex: "var(--token-z-index-menu)", minWidth: 160, width, maxWidth: "var(--token-width-menu)",
            background: "var(--token-menu-background)", border: "1px solid var(--token-border-muted)", borderRadius: "var(--token-menu-radius)", boxShadow: "var(--token-shadow-2)", padding: 4, display: "flex", flexDirection: "column", gap: 2, animation: "fadeIn .15s ease-in" }}>
          {items ? items.map((it, i) => (it.divider ? <div key={i} style={{ height: 1, background: "var(--token-border-muted)", margin: "2px 0" }}></div> : <MenuItem key={i} {...it} />)) : children}
        </div>
      )}
    </div>
  );
}
