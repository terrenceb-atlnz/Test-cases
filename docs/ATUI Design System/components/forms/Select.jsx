import React from "react";
import { SelectOption } from "./SelectOption.jsx";
import { Icon } from "../core/Icon.jsx";
import { Button } from "../actions/Button.jsx";
import { FieldHeader } from "./FormLabel.jsx";
import { InputShell } from "./Input.jsx";

/** at-select — single-choice dropdown. options: [{value,label,disabled}] */
export function Select({ label, hint_text, info_text, error_text, placeholder = "Select", required, invalid, disabled, readonly, options = [], value, clearable, onChange, width }) {
  const [open, setOpen] = React.useState(false);
  const [v, setV] = React.useState(value);
  const ref = React.useRef();
  React.useEffect(() => setV(value), [value]);
  React.useEffect(() => {
    if (!open) return;
    const off = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", off);
    return () => document.removeEventListener("mousedown", off);
  }, [open]);
  const cur = options.find((o) => o.value === v);
  const pick = (x) => { setV(x); setOpen(false); onChange && onChange(x); };
  return (
    <div ref={ref} style={{ position: "relative", display: "flex", flexDirection: "column", width: width || "var(--token-width-input-md)" }}>
      <FieldHeader label={label} required={required} info_text={info_text} hint_text={hint_text} />
      <div role="combobox" aria-expanded={open} tabIndex={disabled ? -1 : 0} onClick={() => !disabled && !readonly && setOpen(!open)} style={{ cursor: disabled ? "default" : "pointer" }}>
        <InputShell focused={open} invalid={invalid} disabled={disabled} readonly={readonly} style={{ alignItems: "center" }}>
          <span style={{ flex: 1, minWidth: 0, padding: "0 0 0 var(--token-input-px-lg)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: cur ? "inherit" : "var(--token-text-muted)" }}>{cur ? cur.label ?? cur.value : placeholder}</span>
          {clearable && cur && <Button size="sm" type="secondaryText" icon="cancel" onClick={(e) => { e.stopPropagation(); pick(undefined); }} />}
          {!readonly && <Icon name="chevron_down" style={{ marginRight: 8, transform: open ? "rotate(180deg)" : "none", transition: "transform 150ms" }} />}
        </InputShell>
      </div>
      {open && (
        <ul role="listbox" style={{ position: "absolute", top: "100%", left: 0, right: 0, marginTop: 4, zIndex: "var(--token-z-index-menu)", listStyle: "none", padding: 4, background: "var(--token-menu-background)", border: "1px solid var(--token-border-muted)", borderRadius: "var(--token-menu-radius)", boxShadow: "var(--token-shadow-2)", maxHeight: 240, overflowY: "auto", display: "flex", flexDirection: "column", gap: 2 }}>
          {options.map((o) => <SelectOption key={o.value} {...o} is_active={o.value === v} onClick={() => pick(o.value)} />)}
        </ul>
      )}
      {error_text && invalid && <span style={{ color: "var(--token-text-error)", fontSize: "var(--token-font-size-sm)" }}>{error_text}</span>}
    </div>
  );
}
