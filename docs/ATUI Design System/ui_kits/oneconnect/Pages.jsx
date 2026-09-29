// Dashboard (widget grid of ATUI charts) + Events log + AI assistant rail.
const D = window.ATUIDesignSystem_dbdde4;

function Widget({ title, subtitle, children }) {
  return <D.Card card_title={title} subtitle={subtitle} header_actions={<D.Button type="secondaryText" size="md" icon="overflow_menu" />} style={{ height: "100%" }}>{children}</D.Card>;
}

function DashboardPage() {
  const [range, setRange] = React.useState("24h");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, padding: 16 }}>
      <D.Header header_title="Dashboard" padding={false} actions={<><D.ButtonGroup options={[{ value: "1h", label: "1h" }, { value: "24h", label: "24h" }, { value: "7d", label: "7d" }]} value={range} onChange={setRange} /><D.Button type="primaryOutline" icon="add" label="Add Widget" /></>} />
      <D.Dashboard>
        <Widget span={3} title="Wireless clients"><D.ChartTrend value="1,284" delta={4.2} data={[8, 9, 7, 10, 12, 11, 14, 13]} /></Widget>
        <Widget span={3} title="Devices online"><D.ChartTrend value="71" unit="/ 75" delta={-1.3} data={[75, 74, 74, 73, 72, 72, 71]} /></Widget>
        <Widget span={6} title="Device status" subtitle="All sites"><D.ChartBreakdown palette="device-status" data={[{ label: "Up", value: 71 }, { label: "Degraded", value: 2 }, { label: "Down", value: 1 }, { label: "Unknown", value: 1 }]} /></Widget>
        <Widget span={8} title="Throughput" subtitle={"Last " + range}><D.ChartBarLine height={200} labels={["00", "03", "06", "09", "12", "15", "18", "21"]} series={[{ name: "Rx (Gbps)", data: [2.1, 1.4, 1.2, 4.8, 6.2, 5.9, 4.1, 3.0] }, { name: "Tx (Gbps)", data: [1.2, 0.9, 0.8, 2.9, 3.8, 3.5, 2.6, 1.9] }]} /></Widget>
        <Widget span={4} title="Events by severity"><D.ChartDonut palette="events" center_label="Events" size={140} data={[{ label: "Critical", value: 4 }, { label: "Warning", value: 11 }, { label: "OK", value: 32 }]} /></Widget>
        <Widget span={4} title="Core switch CPU"><div style={{ display: "flex", justifyContent: "space-around" }}><D.ChartGauge value={38} label="AT-x950-core-01" size={140} /><D.ChartGauge value={76} label="AT-x950-core-02" size={140} /></div></Widget>
        <Widget span={8} title="Top sites by open events">
          {[["Christchurch Warehouse", "bad", 7], ["Wellington Office", "warn", 3], ["Hamilton Branch", "good", 1]].map(([n, h, c]) => (
            <D.ListItem key={n} size="md" item_title={n} icon={null}><D.HealthDot status={h} size="sm" /><D.Badge label={c + " open"} type={h === "bad" ? "error" : h === "warn" ? "warning" : "default"} /></D.ListItem>
          ))}
        </Widget>
      </D.Dashboard>
    </div>
  );
}

const EVENTS = [
  { id: 1, sev: "bad", title: "Device unreachable", device: "AT-TQ6702-lobby", site: "Christchurch Warehouse", t: Date.now() - 6 * 60e3 },
  { id: 2, sev: "warn", title: "High CPU utilisation", device: "AT-x950-core-02", site: "Auckland HQ", t: Date.now() - 22 * 60e3 },
  { id: 3, sev: "warn", title: "Port flapping on port1.0.12", device: "AT-x530-wlg-01", site: "Wellington Office", t: Date.now() - 55 * 60e3 },
  { id: 4, sev: "good", title: "Firmware upgrade completed", device: "AT-x230-ham-01", site: "Hamilton Branch", t: Date.now() - 3 * 3600e3 },
  { id: 5, sev: "bad", title: "PoE budget exceeded", device: "AT-GS980MX-ch-02", site: "Christchurch Warehouse", t: Date.now() - 5 * 3600e3 },
];

function EventsPage() {
  const [tab, setTab] = React.useState("log");
  const [filters, setFilters] = React.useState({});
  const sev = filters.Severity || [];
  const map = { Critical: "bad", Warning: "warn", OK: "good" };
  const rows = EVENTS.filter((e) => !sev.length || sev.some((s) => map[s] === e.sev)).map((e) => ({ ...e, sevCell: { status: e.sev, label: { bad: "Critical", warn: "Warning", good: "OK" }[e.sev] }, what: { title: e.title, subtitle: e.device } }));
  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      <D.Header header_title="Events" actions={<><D.TimeRange /><D.ReloadButton /></>} />
      <div style={{ padding: "0 16px" }}>
        <D.Tabs active_tab={tab} onChange={setTab} tabs={[{ id: "log", title: "Event Log" }, { id: "rules", title: "Rules" }, { id: "syslog", title: "Syslog" }]}>
          {(t) => t === "log" ? (
            <div style={{ paddingTop: 8 }}>
              <D.TableActions placeholder="Search events" filters={<D.TableFilterMenu filters={[{ field: "Severity", header: "Severity", options: ["Critical", "Warning", "OK"] }]} value={filters} onChange={setFilters} />} onExport={() => {}} />
              <D.Table selectable rows={rows} columns={[{ field: "sevCell", header: "Severity", cell: "status", width: 140 }, { field: "what", header: "Event", cell: "titleSubtitle" }, { field: "site", header: "Site" }, { field: "t", header: "Time", cell: "relative" }]} />
            </div>
          ) : <D.Placeholder icon="events" placeholder_title={t === "rules" ? "No rules yet" : "Syslog is not configured"} content={t === "rules" ? "Create a rule to be notified when an event matches." : "Forward device syslog to OneConnect to see it here."} actions={t === "rules" ? <D.Button label="New Rule" icon="add" /> : null} />}
        </D.Tabs>
      </div>
    </div>
  );
}

function AssistantRail({ open, onClose }) {
  if (!open) return null;
  return (
    <aside style={{ width: "var(--token-width-panel-sm)", flex: "none", borderLeft: "1px solid var(--token-sidebar-border)", display: "flex", flexDirection: "column", background: "var(--token-surface-foreground)", minHeight: 0 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 4, padding: 8, borderBottom: "1px solid var(--token-border-muted)" }}>
        <div style={{ display: "flex", gap: 2 }}><D.Button type="secondaryText" icon="time" label="Chat History" /><D.Button type="secondaryText" icon="chat" label="New Chat" /></div>
        <D.Button type="secondaryText" size="md" icon="close" onClick={onClose} />
      </div>
      <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
        <D.PromptThread messages={[{ role: "user", content: "Why is Christchurch Warehouse critical?" }, { role: "assistant", content: "2 devices at Christchurch Warehouse are down: AT-TQ6702-lobby has been unreachable for 6 minutes, and AT-GS980MX-ch-02 exceeded its PoE budget 5 hours ago. Want me to open the event log filtered to this site?" }]} />
        <div style={{ padding: 12 }}><D.PromptInput placeholder="Ask about your network…" /></div>
      </div>
    </aside>
  );
}

Object.assign(window, { DashboardPage, EventsPage, AssistantRail });
