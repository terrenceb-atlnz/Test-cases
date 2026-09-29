import React from "react";
import { FieldHeader } from "./FormLabel.jsx";
import { InputShell, inputFieldStyle } from "./Input.jsx";

/** at-textarea — multi-line input. */
export function Textarea({ label, hint_text, info_text, error_text, placeholder, required, invalid, disabled, readonly, value, rows = 4, max_length, onChange }) {
  const [v, setV] = React.useState(value || "");
  const [f, setF] = React.useState(false);
  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      <FieldHeader label={label} required={required} info_text={info_text} hint_text={hint_text} />
      <InputShell focused={f} invalid={invalid} disabled={disabled} readonly={readonly} style={{ height: "auto" }}>
        <textarea rows={rows} value={v} maxLength={max_length} placeholder={placeholder} disabled={disabled} readOnly={readonly} onFocus={() => setF(true)} onBlur={() => setF(false)} onChange={(e) => { setV(e.target.value); onChange && onChange(e.target.value); }}
          style={{ ...inputFieldStyle, resize: "vertical", padding: "var(--token-input-py) var(--token-input-px-lg)", lineHeight: "var(--token-line-height-base)", fontFamily: "inherit" }} />
      </InputShell>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        {error_text && invalid ? <span style={{ color: "var(--token-text-error)", fontSize: "var(--token-font-size-sm)" }}>{error_text}</span> : <span></span>}
        {max_length && <span style={{ color: "var(--token-text-muted)", fontSize: "var(--token-font-size-xs)" }}>{v.length}/{max_length}</span>}
      </div>
    </div>
  );
}
