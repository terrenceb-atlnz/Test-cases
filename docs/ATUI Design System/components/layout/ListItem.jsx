import React from "react";
import { Icon } from "../core/Icon.jsx";

const SIZE = { xs: [16, "var(--token-font-size-sm)"], sm: [32, "var(--token-font-size-sm)"], md: [40, "var(--token-font-size-body)"], lg: [48, "var(--token-font-size-body)"] };

/** at-list-item — key:value row with bottom hairline. */
export function ListItem({ item_prefix, item_title, subtitle, content, size = "sm", selectable, icon, children, onClick, style }) {
  const [h, setH] = React.useState(false);
  const [mh, fs] = SIZE[size];
  return (
    <div role="listitem" tabIndex={selectable ? 0 : undefined} onClick={onClick} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{ display: "flex", alignItems: "center", gap: 12, minHeight: mh, padding: "4px 0", fontSize: fs, borderBottom: "1px solid var(--token-border-muted)", cursor: selectable ? "pointer" : undefined, background: selectable && h ? "var(--token-surface-1)" : undefined, ...style }}>
      <div style={{ display: "flex", flex: 1, alignItems: "center", gap: 8, minWidth: 0, whiteSpace: "nowrap" }}>
        {icon && <Icon name={icon} />}
        {item_prefix && <span style={{ color: "var(--token-text-secondary)", marginRight: 4 }}>{item_prefix}</span>}
        <span style={{ display: "flex", flexDirection: item_prefix && subtitle ? "column" : "row", gap: item_prefix && subtitle ? 0 : 4, alignItems: item_prefix && subtitle ? "flex-start" : "baseline", overflow: "hidden", textOverflow: "ellipsis", paddingRight: 8 }}>
          <span>{item_title}</span>
          {subtitle && <span style={{ color: "var(--token-text-secondary)", fontSize: "var(--token-font-size-sm)" }}>{subtitle}</span>}
        </span>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "flex-end", gap: 8, textAlign: "right" }}>
        {children}
        {content && <span>{content}</span>}
      </div>
    </div>
  );
}
