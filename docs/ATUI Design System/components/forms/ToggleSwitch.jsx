import React from "react";
import { Icon } from "../core/Icon.jsx";
import { FormLabel } from "./FormLabel.jsx";

/** at-toggle-switch — 40×20 track, 16px thumb with check/subtract glyph. */
export function ToggleSwitch({ label, hint_text, label_position = "before", show_label = true, disabled, value = false, onChange, style }) {
  const [on, setOn] = React.useState(!!value);
  React.useEffect(() => setOn(!!value), [value]);
  const flip = () => { if (disabled) return; setOn(!on); onChange && onChange(!on); };
  return (
    <div role="switch" aria-checked={on ? "true" : "false"} aria-label={!show_label ? label : undefined} tabIndex={disabled ? -1 : 0}
      onClick={flip} onKeyDown={(e) => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); flip(); } }}
      style={{ display: "flex", width: "fit-content", flexDirection: label_position === "after" ? "row-reverse" : "row", alignItems: "center", gap: 8, padding: 8, borderRadius: "var(--token-input-radius)", cursor: "pointer", ...(disabled ? { pointerEvents: "none", opacity: 0.5, filter: "grayscale(1)" } : null), ...style }}>
      {(label && show_label) || hint_text ? (
        <div style={{ display: "flex", flexDirection: "column", pointerEvents: "none", userSelect: "none" }}>
          {label && show_label && <FormLabel label={label} />}
          {hint_text && <span style={{ color: "var(--token-text-muted)", fontSize: "var(--token-font-size-xs)", lineHeight: 1.25 }}>{hint_text}</span>}
        </div>
      ) : null}
      <div style={{ position: "relative", width: 40, height: 20, flex: "none" }}>
        <span style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 999, border: "1px solid var(--token-border-muted)", boxShadow: "inset 0 1px 1px rgba(0,0,0,.05)", background: on ? "var(--token-state-active-background)" : "var(--token-surface-foreground)", transition: "background-color 150ms ease-in-out" }}>
          <span style={{ position: "absolute", width: 16, height: 16, margin: 2, borderRadius: 999, display: "flex", alignItems: "center", justifyContent: "center", transform: `translateX(${on ? 10 : -10}px)`, transition: "transform 150ms ease-in-out, background-color 150ms ease-in-out",
            background: on ? "var(--token-state-active-foreground)" : "color-mix(in srgb, var(--token-state-disabled-foreground) 40%, transparent)", color: on ? "var(--token-button-foreground-inv)" : "var(--token-text-foreground)" }}>
            <Icon name={on ? "checkmark" : "subtract"} size={14} />
          </span>
        </span>
      </div>
    </div>
  );
}
