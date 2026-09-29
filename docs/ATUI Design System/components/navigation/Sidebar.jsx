import React from "react";
import { Icon } from "../core/Icon.jsx";
import { Badge } from "../feedback/Badge.jsx";

/** at-sidebar-menuitem — 22px icon, medium label, active tint. */
export function SidebarMenuItem({ label, icon, badge, is_active, collapsed, onClick, actions, indent }) {
  const [h, setH] = React.useState(false);
  return (
    <div role="menuitem" tabIndex={0} aria-current={is_active ? "page" : undefined} onClick={onClick} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onClick && onClick(e)}
      style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", boxSizing: "border-box", padding: 8, paddingLeft: indent ? 40 : 8, cursor: "pointer", borderRadius: "var(--token-menu-item-radius)", fontSize: "var(--token-font-size-button)",
        color: is_active ? "var(--token-sidebar-active-foreground)" : "var(--token-sidebar-foreground)", background: is_active ? "var(--token-sidebar-active-background)" : h ? "color-mix(in srgb, var(--token-surface-overlay) 7%, transparent)" : "transparent", transition: "color 150ms" }}>
      <div style={{ display: "flex", alignItems: "center", flexGrow: 1, gap: 10, userSelect: "none", overflow: "hidden", whiteSpace: "nowrap" }}>
        {icon && <Icon name={icon} size={22} />}
        {!collapsed && label && <span style={{ fontWeight: "var(--token-font-weight-med)", overflow: "hidden", textOverflow: "ellipsis" }}>{label}</span>}
        {badge && <Badge type="error" impact="high" label={badge} style={{ position: "absolute", top: -8, left: 22, padding: 2, fontSize: 10 }} />}
      </div>
      {!collapsed && actions}
    </div>
  );
}

/** at-sidebar-submenu — accordion group of sidebar items. */
export function SidebarSubmenu({ label, icon, open: o = false, collapsed, children }) {
  const [open, setOpen] = React.useState(o);
  return (
    <div>
      <SidebarMenuItem label={label} icon={icon} collapsed={collapsed} onClick={() => setOpen(!open)} actions={<Icon name="chevron_down" style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 150ms" }} />} />
      {open && !collapsed && <div style={{ display: "flex", flexDirection: "column", gap: 2, marginTop: 2 }}>{children}</div>}
    </div>
  );
}

/** at-sidebar — app navigation rail (300px, collapses to 50px). */
export function Sidebar({ header, footer, collapsed = false, side = "left", children, style }) {
  return (
    <aside style={{ display: "flex", flexDirection: "column", flex: "none", width: collapsed ? "var(--token-width-sidebar-collapsed)" : "var(--token-width-sidebar)", background: "var(--token-sidebar-background)", [side === "left" ? "borderRight" : "borderLeft"]: "1px solid var(--token-sidebar-border)", transition: "width 300ms cubic-bezier(0.455, 0.03, 0.515, 0.955)", overflow: "hidden", ...style }}>
      {header && <div style={{ padding: collapsed ? "8px 4px" : 8 }}>{header}</div>}
      <nav role="menu" style={{ display: "flex", flexDirection: "column", gap: 2, padding: collapsed ? 4 : 8, flex: 1, overflowY: "auto" }}>{children}</nav>
      {footer && <div style={{ padding: collapsed ? 4 : 8, borderTop: "1px solid var(--token-sidebar-border)" }}>{footer}</div>}
    </aside>
  );
}
