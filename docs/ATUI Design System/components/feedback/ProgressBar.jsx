import React from "react";


const FILL = { success: "--token-feedback-success-accent", warning: "--token-feedback-warning-accent", error: "--token-feedback-error-accent", info: "--token-feedback-info-accent" };

/** at-progress-bar — rounded bar, determinate or indeterminate. */
export function ProgressBar({ percentage = 0, mode = "determinate", type = "info", size = "sm", label_before, label_after, style }) {
  const p = Math.min(100, Math.max(0, Number(percentage) || 0));
  const h = size === "lg" ? 16 : 8;
  return (
    <div role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={mode === "determinate" ? p : undefined} style={{ display: "flex", alignItems: "center", gap: 8, ...style }}>
      {label_before}
      <div style={{ position: "relative", flex: 1, height: h, borderRadius: 999, overflow: "hidden", background: mode === "determinate" ? "var(--token-surface-2)" : "var(--token-surface-1)", boxShadow: "inset 0 0 0 1px var(--token-border-muted)" }}>
        <div style={mode === "determinate" ? { height: "100%", width: p + "%", background: `var(${FILL[type] || FILL.info})`, transition: "width 500ms" } : { position: "absolute", top: 0, height: "100%", width: "30%", left: "-30%", background: `var(${FILL[type] || FILL.info})`, animation: "progress-left 1.6s linear infinite" }}></div>
      </div>
      {label_after}
    </div>
  );
}
