import React from "react";
import { FieldHeader } from "./FormLabel.jsx";

const hoverBg = "color-mix(in srgb, var(--token-surface-overlay) 10%, transparent)";

function ChoiceRow({ role, checked, disabled, onToggle, control, label, hint_text, children, style }) {
  const [h, setH] = React.useState(false);
  return (
    <div role={role} aria-checked={checked ? "true" : "false"} aria-disabled={disabled || undefined} tabIndex={disabled ? -1 : 0}
      onClick={() => !disabled && onToggle()} onKeyDown={(e) => { if (!disabled && (e.key === " " || e.key === "Enter")) { e.preventDefault(); onToggle(); } }}
      onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{ position: "relative", display: "flex", alignItems: "flex-start", gap: 8, width: "100%", padding: 8, borderRadius: "var(--token-input-radius)", cursor: "pointer", boxSizing: "border-box",
        background: checked ? "var(--token-state-active-background)" : h ? hoverBg : "var(--token-input-background)",
        transition: "background-color 150ms ease-in-out", ...(disabled ? { pointerEvents: "none", opacity: 0.6, filter: "grayscale(1)" } : null), ...style }}>
      {control}
      {(label || hint_text || children) && (
        <div style={{ display: "flex", flexDirection: "column", pointerEvents: "none" }}>
          {label && <span style={{ paddingLeft: 4, fontSize: "var(--token-font-size-xs)", fontWeight: "var(--token-font-weight-med)", lineHeight: "16px" }}>{label}</span>}
          {hint_text && <span style={{ paddingLeft: 4, fontSize: "var(--token-font-size-xs)", color: "var(--token-text-muted)" }}>{hint_text}</span>}
          {children}
        </div>
      )}
    </div>
  );
}

/** at-checkbox — padded row, active-background when checked. */
export function Checkbox({ label, hint_text, checked, disabled, indeterminate, onChange, children, style }) {
  const [c, setC] = React.useState(!!checked);
  React.useEffect(() => setC(!!checked), [checked]);
  const ref = React.useRef();
  React.useEffect(() => { if (ref.current) ref.current.indeterminate = !!indeterminate; });
  return (
    <ChoiceRow role="checkbox" checked={c} disabled={disabled} label={label} hint_text={hint_text} style={style}
      onToggle={() => { setC(!c); onChange && onChange(!c); }}
      control={<input ref={ref} type="checkbox" tabIndex={-1} readOnly checked={c} disabled={disabled} style={{ margin: 0, width: 16, height: 16, minWidth: 16, accentColor: "var(--token-state-active-foreground)", pointerEvents: "none" }} />}>
      {children}
    </ChoiceRow>
  );
}

/** at-checkbox-group — labelled stack of checkboxes; value is an array. */
export function CheckboxGroup({ label, hint_text, info_text, required, options = [], value = [], layout = "column", disabled, onChange }) {
  const [sel, setSel] = React.useState(value);
  const toggle = (v) => { const n = sel.includes(v) ? sel.filter((x) => x !== v) : [...sel, v]; setSel(n); onChange && onChange(n); };
  return (
    <div role="group">
      <FieldHeader label={label} hint_text={hint_text} info_text={info_text} required={required} />
      <div style={{ display: "flex", flexDirection: layout, gap: 4 }}>
        {options.map((o) => <Checkbox key={o.value} label={o.label} hint_text={o.hint_text} disabled={disabled || o.disabled} checked={sel.includes(o.value)} onChange={() => toggle(o.value)} />)}
      </div>
    </div>
  );
}

/** at-radio — padded row radio. */
export function Radio({ label, hint_text, checked, disabled, onChange, children, style, group }) {
  return (
    <ChoiceRow role="radio" checked={checked} disabled={disabled} label={label} hint_text={hint_text} style={style} onToggle={() => !checked && onChange && onChange()}
      control={<input type="radio" name={group} tabIndex={-1} readOnly checked={!!checked} disabled={disabled} style={{ margin: 0, width: 16, height: 16, minWidth: 16, accentColor: "var(--token-state-active-foreground)", pointerEvents: "none" }} />}>
      {children}
    </ChoiceRow>
  );
}

/** at-radio-group — single choice from a list. */
export function RadioGroup({ label, hint_text, info_text, required, options = [], value, layout = "column", disabled, onChange }) {
  const [v, setV] = React.useState(value);
  const g = React.useId();
  return (
    <div role="radiogroup">
      <FieldHeader label={label} hint_text={hint_text} info_text={info_text} required={required} />
      <div style={{ display: "flex", flexDirection: layout, gap: 4 }}>
        {options.map((o) => <Radio key={o.value} group={g} label={o.label} hint_text={o.hint_text} disabled={disabled || o.disabled} checked={v === o.value} onChange={() => { setV(o.value); onChange && onChange(o.value); }} />)}
      </div>
    </div>
  );
}
