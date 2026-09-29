import React from "react";
import { FieldHeader } from "./FormLabel.jsx";
import { InputShell, inputFieldStyle } from "./Input.jsx";

/** at-input-date / at-input-time — native date/time picker in the ATUI shell. */
export function InputDate({ label, hint_text, info_text, required, invalid, error_text, disabled, value, type = "date", onChange, width }) {
  const [f, setF] = React.useState(false);
  return (
    <div style={{ display: "flex", flexDirection: "column", width: width || "var(--token-width-input-md)" }}>
      <FieldHeader label={label} required={required} info_text={info_text} hint_text={hint_text} />
      <InputShell focused={f} invalid={invalid} disabled={disabled}>
        <input type={type} defaultValue={value} disabled={disabled} onFocus={() => setF(true)} onBlur={() => setF(false)} onChange={(e) => onChange && onChange(e.target.value)} style={{ ...inputFieldStyle, paddingRight: 8, fontFamily: "inherit" }} />
      </InputShell>
      {error_text && invalid && <span style={{ color: "var(--token-text-error)", fontSize: "var(--token-font-size-sm)" }}>{error_text}</span>}
    </div>
  );
}

export function InputTime(props) { return <InputDate type="time" width="var(--token-width-input-sm)" {...props} />; }
