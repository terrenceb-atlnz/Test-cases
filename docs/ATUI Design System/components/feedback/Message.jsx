import React from "react";
import { Icon } from "../core/Icon.jsx";

const ICON = { error: "error", warning: "warning", success: "success", info: "info_filled", default: "" };
const ACCENT = { error: "--token-feedback-error-accent", warning: "--token-feedback-warning-accent", success: "--token-feedback-success-accent", info: "--token-feedback-info-accent", default: "--token-feedback-foreground" };
const BG = { error: "--token-feedback-error-background", warning: "--token-feedback-warning-background", success: "--token-feedback-success-background", info: "--token-feedback-info-background", default: "--token-feedback-background" };

/** at-message — inline alert / banner. */
export function Message({ type = "default", impact = "high", message_title, content, icon, children, actions, style }) {
  const name = icon || ICON[type];
  return (
    <div style={{ display: "flex", padding: 14, textAlign: "left", borderRadius: "0.3rem", color: "var(--token-text-foreground)", background: impact === "high" ? `var(${BG[type]})` : "transparent", ...style }}>
      {name ? <Icon name={name} style={{ marginRight: 8, color: `var(${ACCENT[type]})` }} /> : <span style={{ width: 16, marginRight: 8, flex: "none" }}></span>}
      <div style={{ display: "flex", width: "100%", justifyContent: "space-between", gap: 4, fontSize: "var(--token-font-size-sm)" }}>
        <div>
          {message_title && <div style={{ marginBottom: 4, fontWeight: "var(--token-font-weight-med)", lineHeight: "var(--token-line-height-base)" }}>{message_title}</div>}
          {content && <div style={{ lineHeight: "var(--token-line-height-base)" }}>{content}</div>}
          {children}
        </div>
        {actions}
      </div>
    </div>
  );
}
