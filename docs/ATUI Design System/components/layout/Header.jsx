import React from "react";
import { Icon } from "../core/Icon.jsx";

const FS = { h1: "--token-font-size-h1", h2: "--token-font-size-h2", h3: "--token-font-size-h3", h4: "--token-font-size-h4", h5: "--token-font-size-h5", h6: "--token-font-size-h6" };

/** at-header — page / section title row with subtitle and right-aligned actions. */
export function Header({ header_title, subtitle, size = "h1", border, padding = true, title_prefix, title_suffix, subtitle_content, actions, icon, style }) {
  const H = FS[size] ? size : "div";
  return (
    <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 8, overflow: "hidden", padding: padding ? 16 : 0, borderBottom: border ? "1px solid var(--token-border-muted)" : undefined, ...style }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, overflow: "hidden" }}>
        {title_prefix}
        <div style={{ display: "flex", flexDirection: "column", flexGrow: 1, overflow: "hidden" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: `var(${FS[size]})` }}>
            {header_title && <H style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "inherit", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{icon && <Icon name={icon} size={20} />}{header_title}</H>}
            {title_suffix}
          </div>
          {subtitle && <span style={{ color: "var(--token-text-secondary)", fontSize: "var(--token-font-size-sm)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{subtitle}</span>}
          {subtitle_content}
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>{actions}</div>
    </div>
  );
}
