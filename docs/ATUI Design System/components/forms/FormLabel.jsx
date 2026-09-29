import React from "react";
import { Icon } from "../core/Icon.jsx";
import { Tooltip } from "../feedback/Tooltip.jsx";

/** at-form-label — xs/medium label, red required star, optional info tooltip. */
export function FormLabel({ label, required, info_text, htmlFor, style }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, ...style }}>
      {(label || required) && (
        <label htmlFor={htmlFor} style={{ display: "flex", gap: 4 }}>
          {label}
          {required && <span style={{ color: "var(--token-text-error)" }}>*</span>}
        </label>
      )}
      {info_text && (
        <Tooltip content={info_text} position="right">
          <Icon name="info" size={13} style={{ color: "var(--token-text-muted)", cursor: "pointer" }} />
        </Tooltip>
      )}
    </div>
  );
}

/** Label + hint block shared by form controls. */
export function FieldHeader({ label, required, info_text, hint_text, htmlFor }) {
  if (!label && !required && !info_text && !hint_text) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", marginBottom: 4 }}>
      {(label || required || info_text) && <FormLabel label={label} required={required} info_text={info_text} htmlFor={htmlFor} />}
      {hint_text && <span style={{ color: "var(--token-text-muted)", marginBottom: 2, fontSize: "var(--token-font-size-xs)", lineHeight: 1.25 }}>{hint_text}</span>}
    </div>
  );
}
