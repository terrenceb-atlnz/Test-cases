import React from "react";


/** at-chart-gauge — semicircle gauge with thresholds (alert palette). */
export function ChartGauge({ value = 0, max = 100, label, unit = "%", thresholds = [70, 90], size = 180 }) {
  const p = Math.min(1, Math.max(0, value / max));
  const colr = value >= thresholds[1] ? "var(--chart-alert-3)" : value >= thresholds[0] ? "var(--chart-alert-2)" : "var(--chart-alert-1)";
  const arc = (f) => { const a = Math.PI * (1 - f); return `${50 + 40 * Math.cos(a)} ${50 - 40 * Math.sin(a)}`; };
  return (
    <div style={{ display: "inline-flex", flexDirection: "column", alignItems: "center" }}>
      <svg viewBox="0 0 100 56" width={size} height={size * 0.56}>
        <path d={`M ${arc(0)} A 40 40 0 0 1 ${arc(1)}`} fill="none" stroke="var(--token-surface-1)" strokeWidth="10" strokeLinecap="round" />
        {p > 0 && <path d={`M ${arc(0)} A 40 40 0 0 1 ${arc(p)}`} fill="none" stroke={colr} strokeWidth="10" strokeLinecap="round" />}
      </svg>
      <span style={{ marginTop: -24, fontSize: "var(--token-font-size-h2)", fontWeight: "var(--token-font-weight-med)", color: "var(--chart-title)" }}>{value}{unit}</span>
      {label && <span style={{ fontSize: "var(--token-font-size-xs)", color: "var(--chart-label)" }}>{label}</span>}
    </div>
  );
}
