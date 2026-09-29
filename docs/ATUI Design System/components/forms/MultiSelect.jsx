import React from "react";
import { Select } from "./Select.jsx";
import { Icon } from "../core/Icon.jsx";
import { Badge } from "../feedback/Badge.jsx";
import { FieldHeader } from "./FormLabel.jsx";
import { InputShell } from "./Input.jsx";
import { Checkbox } from "./Checkbox.jsx";

/** at-multi-select — dropdown with checkbox options; selection shown as chips. */
export function MultiSelect({ label, hint_text, info_text, required, placeholder = "Select", options = [], value = [], disabled, onChange, width }) {
  const [open, setOpen] = React.useState(false);
  const [v, setV] = React.useState(value);
  const ref = React.useRef();
  React.useEffect(() => {
    if (!open) return;
    const off = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", off);
    return () => document.removeEventListener("mousedown", off);
  }, [open]);
  const set = (n) => { setV(n); onChange && onChange(n); };
  const toggle = (x) => set(v.includes(x) ? v.filter((y) => y !== x) : [...v, x]);
  const lbl = (x) => (options.find((o) => o.value === x) || {}).label || x;
  return (
    <div ref={ref} style={{ position: "relative", display: "flex", flexDirection: "column", width: width || "var(--token-width-input-md)" }}>
      <FieldHeader label={label} required={required} info_text={info_text} hint_text={hint_text} />
      <div onClick={() => !disabled && setOpen(!open)} style={{ cursor: "pointer" }}>
        <InputShell focused={open} disabled={disabled} style={{ alignItems: "center", height: "auto", minHeight: "var(--token-input-height)" }}>
          <div style={{ flex: 1, display: "flex", flexWrap: "wrap", gap: 4, padding: "4px 0 4px 6px", minWidth: 0 }}>
            {v.length ? v.map((x) => <Badge key={x} size="sm" label={lbl(x)}><span onClick={(e) => { e.stopPropagation(); toggle(x); }} style={{ display: "inline-flex", cursor: "pointer" }}><Icon name="close" size={10} /></span></Badge>) : <span style={{ color: "var(--token-text-muted)", padding: "2px" }}>{placeholder}</span>}
          </div>
          <Icon name="chevron_down" style={{ marginRight: 8, transform: open ? "rotate(180deg)" : "none", transition: "transform 150ms" }} />
        </InputShell>
      </div>
      {open && (
        <div style={{ position: "absolute", top: "100%", left: 0, right: 0, marginTop: 4, zIndex: "var(--token-z-index-menu)", padding: 4, background: "var(--token-menu-background)", border: "1px solid var(--token-border-muted)", borderRadius: "var(--token-menu-radius)", boxShadow: "var(--token-shadow-2)", maxHeight: 260, overflowY: "auto", display: "flex", flexDirection: "column", gap: 2 }}>
          {options.map((o) => <Checkbox key={o.value} label={o.label ?? o.value} checked={v.includes(o.value)} onChange={() => toggle(o.value)} />)}
        </div>
      )}
    </div>
  );
}
