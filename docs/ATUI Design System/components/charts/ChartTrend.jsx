import React from "react";
import { ChartSparkline } from "./ChartSparkline.jsx";
import { Icon } from "../core/Icon.jsx";

/** at-chart-trend — metric tile: display value, delta with trend arrow, sparkline. */
export function ChartTrend({ label, value, unit, delta, good = "up", data }) {
  const up = delta >= 0;
  const ok = (up && good === "up") || (!up && good === "down");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {label && <span style={{ fontSize: "var(--token-font-size-sm)", color: "var(--token-text-muted)" }}>{label}</span>}
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 12 }}>
        <span style={{ fontSize: "var(--token-font-size-xl)", lineHeight: 1, fontWeight: "var(--token-font-weight-med)", fontVariantNumeric: "tabular-nums" }}>{value}{unit && <span style={{ fontSize: "var(--token-font-size-h4)", color: "var(--token-text-muted)", marginLeft: 4 }}>{unit}</span>}</span>
        {data && <ChartSparkline data={data} />}
      </div>
      {delta !== undefined && <span style={{ display: "inline-flex", alignItems: "center", gap: 2, fontSize: "var(--token-font-size-sm)", color: ok ? "var(--token-text-success)" : "var(--token-text-error)" }}><Icon name={up ? "trend_up" : "trend_down"} size={14} />{Math.abs(delta)}%</span>}
    </div>
  );
}
