// OneConnect shell: header (logo, search, context switcher, help, AI, inbox, account) + left sidebar.
const { Button, Search, Menu, MenuItem, Tooltip, Sidebar, SidebarMenuItem, SidebarSubmenu, Badge, Icon } = window.ATUIDesignSystem_dbdde4;

const NAV = [
  { id: "dashboard", icon: "dashboard", label: "Dashboard" },
  { id: "sites", icon: "location", label: "Sites" },
  { id: "assets", icon: "devices", label: "Assets" },
  { id: "events", icon: "events", label: "Events", badge: "3" },
  { id: "wireless", icon: "wifi", label: "Wireless" },
  { id: "firmware", icon: "upgrade", label: "Firmware" },
  { id: "onboarding", icon: "router", label: "Onboarding" },
  { id: "licensing", icon: "document", label: "Licensing" },
];

function AppHeader({ onAssistant, dark, setDark }) {
  return (
    <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, minHeight: "var(--token-height-navbar)", padding: 8, background: "var(--token-surface-foreground)", borderBottom: "1px solid var(--token-border-muted)", flex: "none" }}>
      <img src={dark ? "../../assets/oneconnect-logo-dark.svg" : "../../assets/oneconnect-logo-light.svg"} alt="OneConnect" width="246" height="25" />
      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <Search placeholder="Search" width="var(--token-width-input-sm)" />
        <Menu align="end" width={240} trigger={<Button type="secondaryOutline" label="Contoso Ltd" icon_after="chevron_down" style={{ minWidth: 132 }} />}
          items={[{ label: "Partner portal" }, { divider: true }, { label: "Contoso Ltd", is_active: true }, { label: "Fabrikam Networks" }, { label: "Northwind Schools" }]} />
        <Tooltip content="Help" position="bottom"><Button type="secondaryText" icon="help" onClick={onAssistant} /></Tooltip>
        <Tooltip content="AI Network Assistant" position="bottom">
          <Button type="secondaryText" onClick={onAssistant}><span style={{ display: "block", width: 20, height: 20, background: "var(--token-text-foreground)", WebkitMask: "url(../../assets/ai-network-assistant-logo.svg) center / contain no-repeat", mask: "url(../../assets/ai-network-assistant-logo.svg) center / contain no-repeat" }}></span></Button>
        </Tooltip>
        <span style={{ position: "relative", display: "inline-flex" }}>
          <Button type="secondaryText" icon="notification" />
          <Badge type="error" impact="high" label="2" style={{ position: "absolute", top: 0, right: 0, padding: "0 3px", fontSize: 10, pointerEvents: "none" }} />
        </span>
        <Menu align="end" width={200} autoclose={false} trigger={<Button type="secondaryText" icon="user" />}>
          <MenuItem label="Theme" icon_after={dark ? "asleep" : "light"} onClick={() => setDark(!dark)} />
          <MenuItem label="Notification preferences" icon_after="notification" />
          <MenuItem label="Logout" icon_after="logout" />
        </Menu>
      </div>
    </header>
  );
}

function AppSidebar({ route, go, collapsed, setCollapsed }) {
  return (
    <Sidebar collapsed={collapsed} footer={
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <SidebarSubmenu icon="user_multiple" label="User Management" collapsed={collapsed}>
          <SidebarMenuItem label="Users" indent onClick={() => go("users")} is_active={route === "users"} />
          <SidebarMenuItem label="Roles" indent />
        </SidebarSubmenu>
        <SidebarMenuItem icon="settings" label="System" collapsed={collapsed} />
        <SidebarMenuItem icon={collapsed ? "menu_expand" : "menu_collapse"} label="Collapse" collapsed={collapsed} onClick={() => setCollapsed(!collapsed)} />
      </div>
    }>
      {NAV.map((n) => <SidebarMenuItem key={n.id} icon={n.icon} label={n.label} badge={n.badge} collapsed={collapsed} is_active={route === n.id} onClick={() => go(n.id)} />)}
    </Sidebar>
  );
}

Object.assign(window, { AppHeader, AppSidebar, NAV });
