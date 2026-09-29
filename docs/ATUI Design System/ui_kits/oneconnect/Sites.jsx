// Sites list (cohort cards + search table), site peek (side panel), delete confirmation (dialog).
const DS = window.ATUIDesignSystem_dbdde4;

const SITES = [
  { id: 1, name: "Auckland HQ", parent: "Contoso Ltd", devices: 42, health: "good", events: 0, updated: Date.now() - 4 * 60e3 },
  { id: 2, name: "Wellington Office", parent: "Contoso Ltd", devices: 18, health: "warn", events: 3, updated: Date.now() - 50 * 60e3 },
  { id: 3, name: "Christchurch Warehouse", parent: "Contoso Ltd", devices: 9, health: "bad", events: 7, updated: Date.now() - 3 * 3600e3 },
  { id: 4, name: "Auckland HQ · Level 3", parent: "Auckland HQ", devices: 14, health: "good", events: 0, updated: Date.now() - 12 * 60e3 },
  { id: 5, name: "Hamilton Branch", parent: "Contoso Ltd", devices: 6, health: "good", events: 1, updated: Date.now() - 26 * 3600e3 },
  { id: 6, name: "Dunedin Lab", parent: "Contoso Ltd", devices: 0, health: "good", events: 0, updated: Date.now() - 4 * 86400e3 },
];
const HLABEL = { good: "Healthy", warn: "Degraded", bad: "Critical" };

function CohortCard({ label, value, health, note, selected, onClick }) {
  return (
    <div role="button" tabIndex={0} aria-pressed={selected} onClick={onClick} style={{ cursor: "pointer", borderRadius: "var(--token-card-radius)", boxShadow: selected ? "0 0 0 2px var(--token-state-active-foreground)" : "none" }}>
      <DS.Card card_title={label} style={{ height: "100%" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span style={{ fontSize: "var(--token-font-size-xl)", fontWeight: 600, lineHeight: 1 }}>{value}</span>
          <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "var(--token-font-size-xs)", color: "var(--token-text-secondary)" }}><DS.HealthDot status={health} size="sm" /><span>{note}</span></div>
        </div>
      </DS.Card>
    </div>
  );
}

function SitesList({ onPeek, onDelete, onNew }) {
  const [cohort, setCohort] = React.useState("all");
  const [q, setQ] = React.useState("");
  const cards = [
    { c: "all", label: "All Sites", value: SITES.length, health: "good", note: "Across Contoso Ltd" },
    { c: "good", label: "Healthy", value: SITES.filter((s) => s.health === "good").length, health: "good", note: "No active issues" },
    { c: "warn", label: "Degraded", value: SITES.filter((s) => s.health === "warn").length, health: "warn", note: "Needs attention" },
    { c: "bad", label: "Critical", value: SITES.filter((s) => s.health === "bad").length, health: "bad", note: "Devices down" },
  ];
  const rows = SITES.filter((s) => (cohort === "all" || s.health === cohort) && s.name.toLowerCase().includes(q.toLowerCase()))
    .map((s) => ({ ...s, nameCell: { title: s.name, subtitle: s.parent }, status: { status: s.health, label: HLABEL[s.health] } }));
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100%" }}>
      <DS.Breadcrumb items={[{ label: "Contoso Ltd" }, { label: "Sites" }]} style={{ padding: "16px 16px 0" }} />
      <DS.Header header_title="Sites" size="h1" actions={<DS.Button label="New Site" icon="add" onClick={onNew} />} />
      <div style={{ display: "flex", flexDirection: "column", gap: 16, padding: "0 16px 16px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16 }}>
          {cards.map((k) => <CohortCard key={k.c} {...k} selected={cohort === k.c && k.c !== "all"} onClick={() => setCohort(k.c)} />)}
        </div>
        {cohort !== "all" && (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <DS.Button type="secondaryText" icon="close" label="Clear Filter" onClick={() => setCohort("all")} />
            <span style={{ fontSize: "var(--token-font-size-xs)", color: "var(--token-text-muted)" }}>{rows.length} of {SITES.length} sites</span>
          </div>
        )}
        <DS.Card padding={false}>
          <div style={{ padding: "0 16px" }}><DS.TableActions placeholder="Search sites" search={q} onSearch={setQ} columns={[{ field: "name", header: "Name" }, { field: "devices", header: "Devices" }]} onExport={() => {}} /></div>
          <DS.Table page_size={10} onRowClick={(r) => onPeek(r)} rows={rows}
            empty={<DS.Placeholder size="sm" icon="location" placeholder_title="No sites match this search." />}
            row_actions={(r) => [{ label: "Open full page", icon: "launch" }, { label: "Edit", icon: "edit" }, { divider: true }, { label: "Delete", icon: "delete", onClick: () => onDelete(r) }]}
            columns={[
              { field: "nameCell", header: "Name", cell: "titleSubtitle", sortValue: (r) => r.name },
              { field: "status", header: "Health", cell: "status", sortValue: (r) => r.health },
              { field: "devices", header: "Devices" },
              { field: "events", header: "Open events", cell: "badgeCount" },
              { field: "updated", header: "Last updated", cell: "relative" },
            ]} />
        </DS.Card>
      </div>
    </div>
  );
}

function SitePeek({ site, onClose, onDelete }) {
  return (
    <DS.SidePanel open={!!site} onClose={onClose} size="lg" padding={false}
      title={site && <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 0" }}><DS.HealthDot status={site.health} /><h2 style={{ fontSize: "var(--token-font-size-h5)", fontWeight: 600 }}>{site.name}</h2></div>}
      actions={<DS.Button type="secondaryOutline" label="Open Full Page" icon="launch" />}>
      {site && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16, padding: "16px 24px" }}>
          {site.health !== "good" && <DS.Message type={site.health === "bad" ? "error" : "warning"} message_title={site.events + " open events"} content="Some devices at this site are not reporting. Review events to see what changed." />}
          <DS.Card card_title="Overview">
            <DS.ListItem item_title="Parent site" content={site.parent} />
            <DS.ListItem item_title="Devices" content={String(site.devices)} />
            <DS.ListItem item_title="Health" content={<DS.Badge type={{ good: "success", warn: "warning", bad: "error" }[site.health]} label={HLABEL[site.health]} />} />
            <DS.ListItem item_title="Last updated" content={<DS.RelativeTime date={site.updated} />} />
          </DS.Card>
          <DS.Card card_title="Device status" subtitle={site.devices + " devices"}>
            <DS.ChartBreakdown palette="device-status" data={[{ label: "Up", value: Math.max(0, site.devices - site.events) }, { label: "Degraded", value: Math.min(site.events, 2) }, { label: "Down", value: Math.max(0, site.events - 2) }, { label: "Unknown", value: 0 }]} />
          </DS.Card>
          <div><DS.Button type="destructiveOutline" label="Delete Site" onClick={() => onDelete(site)} /></div>
        </div>
      )}
    </DS.SidePanel>
  );
}

function DeleteSiteDialog({ site, onClose, onConfirm }) {
  const blocked = site && site.devices > 0;
  return (
    <DS.Dialog open={!!site} onClose={onClose} width="var(--token-width-panel-md)">
      {site && (
        <DS.Card card_title={"Delete " + site.name + "?"} header_actions={<DS.Button type="secondaryText" icon="close" onClick={onClose} />}
          footer={<div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}><DS.Button type="secondaryOutline" label="Cancel" onClick={onClose} />{!blocked && <DS.Button type="destructive" label="Delete Site" onClick={() => onConfirm(site)} />}</div>}>
          {blocked ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <DS.Message type="error" content={site.devices + " device(s) are still assigned to this site. Reassign every device to another site before deleting — a device can never be left without a site."} />
              <div><DS.Button type="secondaryText" label="Reassign Devices" icon_after="launch" /></div>
            </div>
          ) : <DS.Message type="error" content={"This will permanently delete " + site.name + ". This cannot be undone."} />}
        </DS.Card>
      )}
    </DS.Dialog>
  );
}

function NewSitePanel({ open, onClose, onCreate }) {
  const [name, setName] = React.useState("");
  return (
    <DS.SidePanel open={open} onClose={onClose} panel_title="New Site" size="sm" footer={<div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}><DS.Button type="secondaryOutline" label="Cancel" onClick={onClose} /><DS.Button label="Create Site" disabled={!name} onClick={() => { onCreate(name); setName(""); }} /></div>}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <DS.Input label="Site name" required value={name} onChange={setName} placeholder="e.g. Auckland HQ" />
        <DS.Select label="Parent site" value="contoso" width="100%" options={[{ value: "contoso", label: "Contoso Ltd" }, { value: "akl", label: "Auckland HQ" }]} />
        <DS.Textarea label="Address" rows={3} />
        <DS.MultiSelect label="Tags" width="100%" options={[{ value: "office", label: "Office" }, { value: "warehouse", label: "Warehouse" }, { value: "lab", label: "Lab" }]} />
      </div>
    </DS.SidePanel>
  );
}

Object.assign(window, { SitesList, SitePeek, DeleteSiteDialog, NewSitePanel, SITES });
