import React from "react";


const PALETTES = { categorical: 10, sequential: 9, alert: 4, "device-status": 5, "onboarding-status": 6, events: 3 };

const col = (palette, i) => `var(--chart-${palette}-${(i % PALETTES[palette]) + 1})`;

/** at-chart-breakdown — stacked horizontal proportion bar with legend + counts. */
export function ChartBreakdown({ data = [], palette = "device-status", total_label }) {
  const total = data.reduce((a, d) => a + d.value, 0) || 1;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {total_label && <span style={{ fontSize: "var(--token-font-size-sm)", color: "var(--token-text-muted)" }}>{total_label}</span>}
      <div style={{ display: "flex", gap: 2, height: 12, borderRadius: 999, overflow: "hidden" }}>
        {data.filter((d) => d.value).map((d, i) => <div key={d.label} title={`${d.label}: ${d.value}`} style={{ flexBasis: (d.value / total) * 100 + "%", background: col(palette, data.indexOf(d)) }}></div>)}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 16px", fontSize: "var(--token-font-size-sm)" }}>
        {data.map((d, i) => <span key={d.label} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><span style={{ width: 8, height: 8, borderRadius: 2, background: col(palette, i) }}></span><span style={{ color: "var(--token-text-secondary)" }}>{d.label}</span><span style={{ fontWeight: "var(--token-font-weight-med)" }}>{d.value}</span></span>)}
      </div>
    </div>
  );
}
