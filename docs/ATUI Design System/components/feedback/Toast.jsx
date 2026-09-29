import React from "react";
import { Icon } from "../core/Icon.jsx";
import { Button } from "../actions/Button.jsx";

const TICON = { success: ["success", "--token-feedback-success-accent"], warning: ["warning", "--token-feedback-warning-accent"], error: ["error", "--token-feedback-error-accent"], info: ["info_filled", "--token-feedback-info-accent"] };

/** at-toaster toast — card with icon, title, message, optional action and countdown bar. */
export function Toast({ type = "info", toast_title, message, action, onClose, progress = 1, style }) {
  const [ic, ac] = TICON[type] || TICON.info;
  return (
    <div style={{ pointerEvents: "auto", minWidth: "var(--token-width-panel-xs)", maxWidth: "var(--token-width-panel-sm)", boxShadow: "var(--token-shadow-1)", borderRadius: 4, overflow: "hidden", display: "flex", flexDirection: "column", background: "var(--token-feedback-background)", border: "1px solid var(--token-border-muted)", animation: "animInUp 300ms ease-out", ...style }}>
      <div style={{ display: "flex", gap: 8, padding: 12, alignItems: "flex-start" }}>
        <Icon name={ic} style={{ color: `var(${ac})`, marginTop: 1 }} />
        <div style={{ flex: 1, fontSize: "var(--token-font-size-sm)" }}>
          {toast_title && <div style={{ fontWeight: "var(--token-font-weight-med)", marginBottom: 2 }}>{toast_title}</div>}
          {message && <div style={{ color: "var(--token-text-secondary)" }}>{message}</div>}
        </div>
        {action}
        {onClose && <Button size="sm" type="secondaryText" icon="close" onClick={onClose} />}
      </div>
      <div style={{ height: 3, background: "var(--token-border-muted)" }}><div style={{ height: "100%", width: "100%", transform: `scaleX(${progress})`, transformOrigin: "left", background: `var(${ac})`, transition: "transform 100ms linear" }}></div></div>
    </div>
  );
}

/** at-toaster — fixed stack of toasts in a viewport corner. */
export function Toaster({ toasts = [], position = "top-right", onDismiss }) {
  const pos = { "top-right": { top: 12, right: 12, alignItems: "flex-end" }, "top-left": { top: 12, left: 12 }, "bottom-right": { bottom: 12, right: 12, alignItems: "flex-end" }, "bottom-left": { bottom: 12, left: 12 } }[position];
  return (
    <div style={{ position: "fixed", zIndex: "var(--token-z-index-modal)", display: "flex", flexDirection: "column", gap: 8, padding: 12, pointerEvents: "none", ...pos }}>
      {toasts.map((t) => <Toast key={t.id} {...t} onClose={() => onDismiss && onDismiss(t.id)} />)}
    </div>
  );
}
