import React from "react";
import { Icon } from "../core/Icon.jsx";
import { FieldHeader } from "./FormLabel.jsx";

const glow = "0 0 0 3px color-mix(in srgb, var(--token-state-active-accent) 50%, transparent)";
const errGlow = "0 0 0 3px color-mix(in srgb, var(--token-state-error-accent) 50%, transparent)";

/** Shared bordered input shell (36px, radius-md, active focus ring). */
export function InputShell({ focused, invalid, disabled, readonly, children, style }) {
  return (
    <div style={{
      position: "relative", display: "flex", alignItems: "stretch", width: "100%", minHeight: "var(--token-input-height)", height: "var(--token-input-height)", gap: 4, overflow: "hidden",
      borderRadius: "var(--token-input-radius)", border: disabled || readonly ? "1px solid transparent" : `1px solid ${invalid ? "var(--token-border-error)" : focused ? "var(--token-state-active-accent)" : "var(--token-border-muted)"}`,
      background: disabled || readonly ? "var(--token-surface-1)" : "var(--token-input-background)", color: disabled ? "var(--token-text-disabled)" : "var(--token-text-foreground)",
      boxShadow: focused && !disabled ? (invalid ? errGlow : glow) : "none", pointerEvents: disabled ? "none" : undefined,
      transition: "border-color 150ms ease-in-out, box-shadow 150ms ease-in-out, background-color 150ms ease-in-out", ...style,
    }}>{children}</div>
  );
}

export const inputFieldStyle = { flex: 1, minWidth: 0, border: 0, outline: 0, background: "transparent", padding: "var(--token-input-py) 0 var(--token-input-py) var(--token-input-px-lg)", textOverflow: "ellipsis", fontSize: "var(--token-font-size-body)", color: "inherit" };

/** at-input — text input with label, hint, info tooltip, validation and clear. */
export function Input({ label, type = "text", hint_text, info_text, error_text, placeholder = "", required, invalid, readonly, disabled, clearable, value, onChange, actions, style, width }) {
  const [v, setV] = React.useState(value ?? "");
  const [focused, setFocused] = React.useState(false);
  const id = React.useId();
  React.useEffect(() => { if (value !== undefined) setV(value); }, [value]);
  const set = (x) => { setV(x); onChange && onChange(x); };
  return (
    <div style={{ display: "flex", flexDirection: "column", width: width || "100%", ...style }}>
      <FieldHeader label={label} required={required && !readonly} info_text={info_text} hint_text={hint_text} htmlFor={id} />
      <InputShell focused={focused} invalid={invalid} disabled={disabled} readonly={readonly}>
        <input id={id} type={type} value={v} placeholder={placeholder} readOnly={readonly} disabled={disabled} onChange={(e) => set(e.target.value)} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} style={inputFieldStyle} />
        <div style={{ display: "flex", alignItems: "center", padding: "4px 4px 4px 0" }}>
          {actions}
          {clearable && !readonly && !disabled && v && (
            <span role="button" tabIndex={0} aria-label="Clear" onClick={() => set("")} style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: 24, height: 24, borderRadius: "var(--token-button-radius)", cursor: "pointer", color: "var(--token-text-foreground)" }}>
              <Icon name="cancel" />
            </span>
          )}
        </div>
      </InputShell>
      {error_text && invalid && <span style={{ color: "var(--token-text-error)", fontSize: "var(--token-font-size-sm)" }}>{error_text}</span>}
    </div>
  );
}
