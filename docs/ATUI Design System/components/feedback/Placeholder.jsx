import React from "react";
import { Icon } from "../core/Icon.jsx";

/** at-placeholder — empty / zero state with icon, title, body and actions. */
export function Placeholder({ placeholder_title, content, icon = "data_table", size = "md", actions, style }) {
  const s = size === "sm";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", gap: 8, padding: s ? 16 : 32, borderRadius: "var(--token-placeholder-radius)", ...style }}>
      {icon && <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: s ? 40 : 56, height: s ? 40 : 56, borderRadius: 999, background: "var(--token-surface-1)", color: "var(--token-text-muted)" }}><Icon name={icon} size={s ? 20 : 24} /></span>}
      {placeholder_title && <div style={{ fontSize: s ? "var(--token-font-size-h5)" : "var(--token-font-size-h4)", fontWeight: "var(--token-font-weight-med)" }}>{placeholder_title}</div>}
      {content && <div style={{ color: "var(--token-text-muted)", fontSize: "var(--token-font-size-sm)", maxWidth: 360, textWrap: "pretty" }}>{content}</div>}
      {actions && <div style={{ display: "flex", gap: 8, marginTop: 4 }}>{actions}</div>}
    </div>
  );
}
