import React from "react";
import { Button } from "../actions/Button.jsx";
import { FieldHeader } from "./FormLabel.jsx";
import { InputShell, inputFieldStyle } from "./Input.jsx";

/** at-input-numeric — number field with −/+ steppers. Put the unit in the label: "Timeout (seconds)". */
export function InputNumeric({ label, hint_text, info_text, error_text, required, invalid, disabled, readonly, value = 0, min, max, step = 1, onChange, width }) {
  const [v, setV] = React.useState(value);
  const [f, setF] = React.useState(false);
  const set = (n) => { if (min !== undefined) n = Math.max(min, n); if (max !== undefined) n = Math.min(max, n); setV(n); onChange && onChange(n); };
  return (
    <div style={{ display: "flex", flexDirection: "column", width: width || "var(--token-width-input-sm)" }}>
      <FieldHeader label={label} required={required} info_text={info_text} hint_text={hint_text} />
      <InputShell focused={f} invalid={invalid} disabled={disabled} readonly={readonly} style={{ alignItems: "center" }}>
        {!readonly && <div style={{ paddingLeft: 4 }}><Button size="sm" type="secondaryText" icon="subtract" disabled={min !== undefined && v <= min} onClick={() => set(Number(v) - step)} /></div>}
        <input type="number" value={v} onChange={(e) => set(Number(e.target.value))} onFocus={() => setF(true)} onBlur={() => setF(false)} readOnly={readonly} disabled={disabled} style={{ ...inputFieldStyle, textAlign: "center", padding: 0, MozAppearance: "textfield" }} />
        {!readonly && <div style={{ paddingRight: 4 }}><Button size="sm" type="secondaryText" icon="add" disabled={max !== undefined && v >= max} onClick={() => set(Number(v) + step)} /></div>}
      </InputShell>
      {error_text && invalid && <span style={{ color: "var(--token-text-error)", fontSize: "var(--token-font-size-sm)" }}>{error_text}</span>}
    </div>
  );
}
