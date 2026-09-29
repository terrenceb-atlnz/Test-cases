import React from "react";


/** at-chart-sparkline — tiny inline line/area. */
export function ChartSparkline({ data = [], width = 100, height = 28, color = "var(--chart-sequential-6)", area = true }) {
  const mx = Math.max(...data), mn = Math.min(...data), rg = mx - mn || 1;
  const pts = data.map((v, i) => [(i / (data.length - 1)) * width, height - 2 - ((v - mn) / rg) * (height - 4)]);
  const d = pts.map((p) => p.join(",")).join(" ");
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: "block" }}>
      {area && <polygon points={`0,${height} ${d} ${width},${height}`} fill={color} opacity="0.15" />}
      <polyline points={d} fill="none" stroke={color} strokeWidth="1.5" />
    </svg>
  );
}
