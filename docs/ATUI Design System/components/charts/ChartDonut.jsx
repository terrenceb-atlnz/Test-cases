import React from "react";


const PALETTES = { categorical: 10, sequential: 9, alert: 4, "device-status": 5, "onboarding-status": 6, events: 3 };

const col = (palette, i) => `var(--chart-${palette}-${(i % PALETTES[palette]) + 1})`;

/** at-chart-donut — ring with centre total and legend. data: [{label, value}] */
export function ChartDonut({ data = [], palette = "categorical", size = 160, center_label = "Total", show_legend = true }) {
  const total = data.reduce((a, d) => a + d.value, 0) || 1;
  const r = 42, c = 2 * Math.PI * r;
  let off = 0;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 24, flexWrap: "wrap" }}>
      <div style={{ position: "relative", width: size, height: size }}>
        <svg viewBox="0 0 100 100" width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
          <circle cx="50" cy="50" r={r} fill="none" stroke="var(--token-surface-1)" strokeWidth="12" />
          {data.map((d, i) => { const len = (d.value / total) * c; const el = <circle key={i} cx="50" cy="50" r={r} fill="none" stroke={col(palette, i)} strokeWidth="12" strokeDasharray={`${Math.max(0, len - 1)} ${c}`} strokeDashoffset={-off} />; off += len; return el; })}
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontSize: "var(--token-font-size-h2)", fontWeight: "var(--token-font-weight-med)", color: "var(--chart-title)" }}>{data.reduce((a, d) => a + d.value, 0)}</span>
          <span style={{ fontSize: "var(--token-font-size-xs)", color: "var(--chart-label)" }}>{center_label}</span>
        </div>
      </div>
      {show_legend && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: "var(--token-font-size-sm)" }}>
          {data.map((d, i) => <span key={d.label} style={{ display: "flex", alignItems: "center", gap: 8 }}><span style={{ width: 8, height: 8, borderRadius: 2, background: col(palette, i) }}></span><span style={{ flex: 1, color: "var(--token-text-secondary)" }}>{d.label}</span><span style={{ fontVariantNumeric: "tabular-nums" }}>{d.value}</span></span>)}
        </div>
      )}
    </div>
  );
}
