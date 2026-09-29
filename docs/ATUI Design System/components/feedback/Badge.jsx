import React from "react";
import { Icon } from "../core/Icon.jsx";

const mix = (v, p) => `color-mix(in srgb, var(${v}) ${p}%, transparent)`;
const LOW = {
  default: ["--token-feedback-foreground", "--token-feedback-background", "1px solid var(--token-border-default)"],
  success: ["--token-feedback-success-foreground", "--token-feedback-success-background"],
  warning: ["--token-feedback-warning-foreground", "--token-feedback-warning-background"],
  error: ["--token-feedback-error-foreground", "--token-feedback-error-background"],
  info: ["--token-feedback-info-foreground", "--token-feedback-info-background"],
  disabled: ["--token-state-disabled-foreground", "--token-state-disabled-background"],
};
const HIGH = {
  default: ["--token-feedback-foreground", "--token-feedback-background-inv", "1px solid var(--token-border-default)"],
  success: ["--token-feedback-success-foreground-inv", "--token-feedback-success-background-inv"],
  warning: ["--token-feedback-warning-foreground-inv", "--token-feedback-warning-background-inv"],
  error: ["--token-feedback-error-foreground-inv", "--token-feedback-error-background-inv"],
  info: ["--token-feedback-info-foreground-inv", "--token-feedback-info-background-inv"],
  disabled: ["--token-state-disabled-foreground-inv", "--token-state-disabled-background-inv"],
};

/** at-badge — small status / label pill. */
export function Badge({ label, type = "default", size = "sm", impact = "low", rounded = false, icon, children, style }) {
  const [fg, bg, border] = (impact === "high" ? HIGH : LOW)[type] || LOW.default;
  const b = border || (impact === "low" ? `1px solid ${mix(fg, 30)}` : "1px solid transparent");
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 2, whiteSpace: "nowrap", cursor: "default", fontWeight: "var(--token-font-weight-light)",
      lineHeight: "0.9286rem", borderRadius: rounded ? 999 : "var(--token-badge-radius)", color: `var(${fg})`, background: `var(${bg})`, border: b,
      ...(size === "lg" ? { padding: "4px 6px", fontSize: "var(--token-font-size-sm)" } : { padding: "2px 4px", fontSize: "var(--token-font-size-xs)" }), ...style,
    }}>
      {icon && <Icon name={icon} size={12} />}
      {label && <span>{label}</span>}
      {children}
    </span>
  );
}
