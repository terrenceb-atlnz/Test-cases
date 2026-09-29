import React from "react";
import { Icon } from "../core/Icon.jsx";

/** at-breadcrumb — trail of links separated by chevrons; last item is active. items: [{label,onClick}] */
export function Breadcrumb({ items = [], style }) {
  return (
    <nav aria-label="Breadcrumb" style={{ display: "flex", alignItems: "center", flexWrap: "wrap", fontSize: "var(--token-font-size-body)", ...style }}>
      {items.map((it, i) => {
        const last = i === items.length - 1;
        return (
          <React.Fragment key={i}>
            {last ? <span aria-current="page" style={{ color: "var(--token-state-active-accent)", padding: "2px 8px", cursor: "default" }}>{it.label}</span>
              : <BreadLink onClick={it.onClick}>{it.label}</BreadLink>}
            {!last && <Icon name="chevron_right" size={14} style={{ color: "var(--token-text-muted)" }} />}
          </React.Fragment>
        );
      })}
    </nav>
  );
}

function BreadLink({ children, onClick }) {
  const [h, setH] = React.useState(false);
  return <a role="link" tabIndex={0} onClick={onClick} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)} style={{ padding: "2px 8px", borderRadius: "var(--token-border-radius-lg)", cursor: "pointer", color: h ? "var(--token-text-foreground)" : "var(--token-text-muted)", textDecoration: h ? "underline" : "none", transition: "color 150ms ease-in-out" }}>{children}</a>;
}
