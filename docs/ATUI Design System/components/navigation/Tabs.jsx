import React from "react";

const glow = "0 0 0 3px color-mix(in srgb, var(--token-state-active-accent) 50%, transparent)";

function Trigger({ tab, active, layout, fill, onClick }) {
  const [h, setH] = React.useState(false);
  const vert = layout === "vertical";
  return (
    <div role="tab" tabIndex={0} aria-selected={active} data-active={active ? "true" : "false"} onClick={onClick} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onClick()}
      style={{ display: vert ? "flex" : "inline-flex", justifyContent: vert ? "flex-start" : "center", alignItems: "center", gap: 4, padding: 8, cursor: "pointer", borderRadius: "var(--token-input-radius)", border: "1px solid transparent",
        fontSize: "var(--token-font-size-button)", fontWeight: "var(--token-font-weight-med)", flex: fill ? 1 : undefined, transition: "color 150ms ease-in-out, background-color 150ms ease-in-out",
        color: active ? (vert ? "var(--token-state-active-foreground)" : "var(--token-state-active-accent)") : h ? "var(--token-text-foreground)" : "var(--token-text-muted)",
        background: active && vert ? "var(--token-state-active-background)" : "transparent" }}>
      {tab.title}
      {tab.suffix}
    </div>
  );
}

/** at-tabs — horizontal (underline indicator) or vertical tab list. tabs: [{id,title}] */
export function Tabs({ tabs = [], active_tab, layout = "horizontal", fill, onChange, nav_content, children, style }) {
  const [a, setA] = React.useState(active_tab ?? tabs[0]?.id);
  React.useEffect(() => { if (active_tab !== undefined) setA(active_tab); }, [active_tab]);
  const nav = React.useRef();
  const [ind, setInd] = React.useState({ left: 0, width: 0, opacity: 0 });
  React.useLayoutEffect(() => {
    if (!nav.current || layout !== "horizontal") return;
    const el = nav.current.querySelector('[data-active="true"]');
    if (!el) return;
    const c = nav.current.getBoundingClientRect(), b = el.getBoundingClientRect();
    setInd({ left: b.left - c.left, width: b.width - 16, opacity: 1 });
  }, [a, tabs.length, layout]);
  const pick = (id) => { setA(id); onChange && onChange(id); };
  const body = typeof children === "function" ? children(a) : children;
  if (layout === "vertical") {
    return (
      <div style={{ display: "flex", flex: 1, ...style }}>
        <nav role="tablist" style={{ display: "flex", flexDirection: "column", padding: 16, minWidth: 200 }}>
          {tabs.map((t) => <Trigger key={t.id} tab={t} layout="vertical" active={a === t.id} onClick={() => pick(t.id)} />)}
        </nav>
        <div role="tabpanel" style={{ display: "flex", flexDirection: "column", flex: 1 }}>{body}</div>
      </div>
    );
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", ...style }}>
      <nav ref={nav} role="tablist" style={{ position: "relative", display: "flex", flexWrap: "wrap", alignItems: "center", gap: 2, padding: "0 2px", borderBottom: "1px solid var(--token-border-muted)" }}>
        {tabs.map((t) => <Trigger key={t.id} tab={t} layout="horizontal" fill={fill} active={a === t.id} onClick={() => pick(t.id)} />)}
        {nav_content && <div style={{ marginLeft: "auto" }}>{nav_content}</div>}
        <div aria-hidden="true" style={{ position: "absolute", bottom: 0, height: 2, margin: "0 8px", borderRadius: "var(--token-border-radius-sm)", background: "var(--token-state-active-accent)", transition: "left 150ms ease-in-out, width 150ms ease-in-out", ...ind }}></div>
      </nav>
      <div role="tabpanel">{body}</div>
    </div>
  );
}
