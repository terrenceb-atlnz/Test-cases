import React from "react";
import { Icon } from "../core/Icon.jsx";

/** at-accordion-item — details/summary row; label trigger with chevron. */
export function AccordionItem({ label, content, open: o = false, border = true, disabled, children, onChange }) {
  const [open, setOpen] = React.useState(o);
  const [h, setH] = React.useState(false);
  return (
    <div data-state={open ? "expanded" : "collapsed"} style={{ borderBottom: border ? "1px solid var(--token-border-muted)" : undefined }}>
      <div role="button" aria-expanded={open} tabIndex={0} onClick={() => { if (disabled) return; setOpen(!open); onChange && onChange(!open); }} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
        style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, padding: "12px 16px", cursor: disabled ? "default" : "pointer", fontWeight: "var(--token-font-weight-med)", color: disabled ? "var(--token-state-disabled-foreground)" : undefined, background: h && !disabled ? "var(--token-surface-1)" : "transparent", transition: "background-color 150ms" }}>
        <span>{label}</span>
        <Icon name="chevron_down" style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 150ms" }} />
      </div>
      {open && <div>{content && <div style={{ display: "flex", flexDirection: "column", padding: 16, lineHeight: "var(--token-line-height-base)" }}>{content}</div>}{children}</div>}
    </div>
  );
}

/** at-accordion — stack of AccordionItems. items: [{label, content}] */
export function Accordion({ items, children, style }) {
  return <div style={{ display: "flex", flexDirection: "column", ...style }}>{items ? items.map((it, i) => <AccordionItem key={i} {...it} />) : children}</div>;
}
