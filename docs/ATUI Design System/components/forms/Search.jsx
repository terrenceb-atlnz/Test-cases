import React from "react";
import { Icon } from "../core/Icon.jsx";
import { Button } from "../actions/Button.jsx";
import { FormLabel } from "./FormLabel.jsx";
import { InputShell, inputFieldStyle } from "./Input.jsx";

/** at-search — search box with leading glyph and clear button. */
export function Search({ label, hint_text, placeholder = "Search", value, onChange, width, style }) {
  const [v, setV] = React.useState(value || "");
  const [f, setF] = React.useState(false);
  const set = (x) => { setV(x); onChange && onChange(x); };
  return (
    <div style={{ display: "flex", flexDirection: "column", width: width || "var(--token-width-input-md)", ...style }}>
      {label && <FormLabel label={label} style={{ marginBottom: 4 }} />}
      <InputShell focused={f} style={{ alignItems: "center" }}>
        <Icon name="search" style={{ padding: "0 8px", boxSizing: "content-box" }} />
        <input role="searchbox" aria-label={label ? undefined : placeholder} value={v} placeholder={placeholder} onChange={(e) => set(e.target.value)} onFocus={() => setF(true)} onBlur={() => setF(false)} style={{ ...inputFieldStyle, padding: 0, marginRight: 4 }} />
        {v && <div style={{ paddingRight: 4 }}><Button size="sm" type="secondaryText" icon="cancel" onClick={() => set("")} /></div>}
      </InputShell>
      {hint_text && <span style={{ color: "var(--token-text-secondary)", marginTop: 4, fontSize: "var(--token-font-size-xs)" }}>{hint_text}</span>}
    </div>
  );
}
