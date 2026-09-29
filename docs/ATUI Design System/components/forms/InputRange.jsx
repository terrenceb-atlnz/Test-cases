import React from "react";
import { FieldHeader } from "./FormLabel.jsx";

/** at-input-range — bounded slider with visible min/max and value. */
export function InputRange({ label, hint_text, info_text, value = 50, min = 0, max = 100, step = 1, disabled, show_value = true, onChange }) {
  const [v, setV] = React.useState(value);
  const pct = ((v - min) / (max - min)) * 100;
  return (
    <div style={{ display: "flex", flexDirection: "column", opacity: disabled ? 0.5 : 1 }}>
      <FieldHeader label={label} info_text={info_text} hint_text={hint_text} />
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ color: "var(--token-text-muted)", fontSize: "var(--token-font-size-xs)" }}>{min}</span>
        <input type="range" min={min} max={max} step={step} value={v} disabled={disabled} onChange={(e) => { setV(Number(e.target.value)); onChange && onChange(Number(e.target.value)); }}
          style={{ flex: 1, height: 4, appearance: "none", WebkitAppearance: "none", borderRadius: 999, background: `linear-gradient(to right, var(--token-state-active-accent) ${pct}%, var(--token-surface-0) ${pct}%)`, accentColor: "var(--token-state-active-accent)", cursor: "pointer" }} />
        <span style={{ color: "var(--token-text-muted)", fontSize: "var(--token-font-size-xs)" }}>{max}</span>
        {show_value && <span style={{ minWidth: 40, textAlign: "center", padding: "4px 8px", border: "1px solid var(--token-border-muted)", borderRadius: "var(--token-input-radius)", fontVariantNumeric: "tabular-nums" }}>{v}</span>}
      </div>
    </div>
  );
}
