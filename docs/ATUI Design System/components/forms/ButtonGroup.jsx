import React from "react";
import { Icon } from "../core/Icon.jsx";
import { FieldHeader } from "./FormLabel.jsx";

const hoverBg = "color-mix(in srgb, var(--token-surface-overlay) 10%, transparent)";

function Seg({ active, disabled, onClick, children, height }) {
  const [h, setH] = React.useState(false);
  return (
    <button type="button" role="radio" aria-checked={!!active} disabled={disabled} onClick={onClick} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{ display: "flex", alignItems: "center", gap: 4, height, padding: "4px 12px", border: "1px solid transparent", borderRadius: "var(--token-input-radius)", lineHeight: 1, fontWeight: "var(--token-font-weight-light)", cursor: disabled ? "default" : "pointer",
        background: active ? "var(--token-state-active-background)" : h && !disabled ? hoverBg : "transparent", color: disabled ? "var(--token-text-disabled)" : active ? "var(--token-state-active-foreground)" : "var(--token-text-foreground)", transition: "background-color 150ms ease-in-out, color 150ms ease-in-out" }}>
      {children}
    </button>
  );
}

const frame = { position: "relative", width: "fit-content", border: "1px solid var(--token-border-muted)", background: "var(--token-input-background)", borderRadius: "var(--token-border-radius-lg)", boxShadow: "inset 0 1px 1px rgba(0,0,0,.05)" };

/** at-button-group — segmented control. options: [{value,label,icon,disabled}] */
export function ButtonGroup({ label, hint_text, info_text, options = [], value, disabled, onChange }) {
  const [v, setV] = React.useState(value ?? options[0]?.value);
  return (
    <div>
      <FieldHeader label={label} hint_text={hint_text} info_text={info_text} />
      <div role="radiogroup" style={frame}>
        <div style={{ display: "flex", margin: 2, gap: 2 }}>
          {options.map((o) => (
            <Seg key={o.value} height={28} active={v === o.value} disabled={disabled || o.disabled} onClick={() => { setV(o.value); onChange && onChange(o.value); }}>
              {o.icon && <Icon name={o.icon} />}
              {o.label ?? (o.icon ? "" : o.value)}
            </Seg>
          ))}
        </div>
      </div>
    </div>
  );
}

/** at-button-switch — Off/On segmented boolean. */
export function ButtonSwitch({ label, hint_text, info_text, value = false, disabled, onChange }) {
  const [v, setV] = React.useState(!!value);
  const set = (x) => { setV(x); onChange && onChange(x); };
  return (
    <div>
      <FieldHeader label={label} hint_text={hint_text} info_text={info_text} />
      <div role="radiogroup" style={frame}>
        <div style={{ display: "flex", margin: 2 }}>
          <Seg height={30} active={!v} disabled={disabled} onClick={() => set(false)}>Off</Seg>
          <Seg height={30} active={v} disabled={disabled} onClick={() => set(true)}>On</Seg>
        </div>
      </div>
    </div>
  );
}
