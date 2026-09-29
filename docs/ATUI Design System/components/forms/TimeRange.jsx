import React from "react";
import { SelectOption } from "./SelectOption.jsx";
import { Button } from "../actions/Button.jsx";
import { FieldHeader } from "./FormLabel.jsx";

/** at-time-range — preset relative ranges + custom option, as a compact select-like trigger. */
export function TimeRange({ label, options = ["Last 15 minutes", "Last hour", "Last 24 hours", "Last 7 days", "Last 30 days", "Custom range"], value, onChange }) {
  const [open, setOpen] = React.useState(false);
  const [v, setV] = React.useState(value || options[2]);
  const ref = React.useRef();
  React.useEffect(() => {
    if (!open) return;
    const off = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", off);
    return () => document.removeEventListener("mousedown", off);
  }, [open]);
  return (
    <div ref={ref} style={{ position: "relative", display: "inline-flex", flexDirection: "column" }}>
      <FieldHeader label={label} />
      <Button type="secondaryOutline" icon="schedule" icon_after="chevron_down" label={v} onClick={() => setOpen(!open)} />
      {open && (
        <ul role="listbox" style={{ position: "absolute", top: "100%", right: 0, marginTop: 4, minWidth: 200, zIndex: "var(--token-z-index-menu)", listStyle: "none", padding: 4, background: "var(--token-menu-background)", border: "1px solid var(--token-border-muted)", borderRadius: "var(--token-menu-radius)", boxShadow: "var(--token-shadow-2)", display: "flex", flexDirection: "column", gap: 2 }}>
          {options.map((o) => <SelectOption key={o} value={o} is_active={o === v} onClick={() => { setV(o); setOpen(false); onChange && onChange(o); }} />)}
        </ul>
      )}
    </div>
  );
}
