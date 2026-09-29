import React from "react";
import { Button } from "../actions/Button.jsx";

/** at-side-panel — slide-in panel from right/left; sticky blurred header + optional footer. */
export function SidePanel({ open, onClose, panel_title, panel_subtitle, size = "xs", origin = "right", backdrop = false, close_backdrop = false, has_close_button = true, padding = true, position = "fixed", actions, title, footer, children }) {
  const w = `var(--token-width-panel-${size})`;
  const bar = { zIndex: 2, position: "sticky", background: "color-mix(in srgb, var(--token-surface-foreground) 80%, transparent)", backdropFilter: "blur(10px)" };
  return (
    <>
      {open && backdrop && <div onMouseDown={() => close_backdrop && onClose && onClose()} style={{ position, inset: 0, zIndex: "var(--token-z-index-nav)", background: "rgba(0,0,0,0.2)" }}></div>}
      <div aria-hidden={!open} style={{ position, top: 0, bottom: 0, [origin]: 0, zIndex: "var(--token-z-index-nav)", width: w, minWidth: "var(--token-width-panel-xs)", maxWidth: "100%", display: "flex", flexDirection: "column", background: "var(--token-surface-foreground)", boxShadow: "var(--token-shadow-md)", overflowX: "hidden", overflowY: "auto",
        transform: open ? "translateX(0)" : `translateX(${origin === "left" ? "-" : ""}100%)`, opacity: open ? 1 : 0, transition: "transform 300ms ease, opacity 300ms ease", pointerEvents: open ? "auto" : "none" }}>
        <header style={{ ...bar, top: 0, padding: "12px 8px 12px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {title}
            {panel_title && <h3 style={{ fontSize: "var(--token-font-size-h4)", fontWeight: "var(--token-font-weight-med)", lineHeight: 1 }}>{panel_title}</h3>}
            {panel_subtitle && <p style={{ margin: 0, fontSize: "var(--token-font-size-sm)", lineHeight: 1 }}>{panel_subtitle}</p>}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            {actions}
            {has_close_button && <Button size="md" type="secondaryText" icon="close" onClick={() => onClose && onClose()} />}
          </div>
        </header>
        <div style={{ display: "flex", flexDirection: "column", flexGrow: footer ? 0 : 1, width: "100%", padding: padding ? 16 : 0 }}>{children}</div>
        {footer && <div style={{ ...bar, bottom: 0, padding: "12px 16px" }}>{footer}</div>}
      </div>
    </>
  );
}
