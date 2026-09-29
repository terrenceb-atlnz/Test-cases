import React from "react";


const PALETTES = { categorical: 10, sequential: 9, alert: 4, "device-status": 5, "onboarding-status": 6, events: 3 };

const col = (palette, i) => `var(--chart-${palette}-${(i % PALETTES[palette]) + 1})`;

const axisText = { fontSize: 11, fill: "var(--chart-label)", fontFamily: "var(--token-font-family-base)" };

function Legend({ items, palette }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px", fontSize: "var(--token-font-size-xs)", color: "var(--chart-label)" }}>
      {items.map((l, i) => <span key={l} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}><span style={{ width: 8, height: 8, borderRadius: 2, background: col(palette, i) }}></span>{l}</span>)}
    </div>
  );
}

/** at-chart-bar-line — bar and/or line series over categories. series: [{name, data:number[], type:"bar"|"line"}] */
export function ChartBarLine({ labels = [], series = [], palette = "categorical", height = 220, stacked = false, show_legend = true }) {
  const W = 600, H = height, P = { l: 36, r: 8, t: 8, b: 24 };
  const bars = series.filter((s) => s.type !== "line"), lines = series.filter((s) => s.type === "line");
  const maxV = Math.max(1, ...labels.map((_, i) => stacked ? bars.reduce((a, s) => a + s.data[i], 0) : Math.max(0, ...bars.map((s) => s.data[i]))), ...lines.flatMap((s) => s.data));
  const nice = Math.ceil(maxV / 4 / Math.pow(10, Math.floor(Math.log10(maxV / 4)))) * Math.pow(10, Math.floor(Math.log10(maxV / 4))) * 4;
  const iw = W - P.l - P.r, ih = H - P.t - P.b, bw = iw / labels.length;
  const y = (v) => P.t + ih - (v / nice) * ih;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="none" style={{ overflow: "visible" }}>
        {[0, 1, 2, 3, 4].map((k) => <g key={k}><line x1={P.l} x2={W - P.r} y1={y((nice / 4) * k)} y2={y((nice / 4) * k)} stroke="var(--chart-axis-line)" strokeDasharray={k ? "2 3" : ""} /><text x={P.l - 6} y={y((nice / 4) * k) + 4} textAnchor="end" style={axisText}>{(nice / 4) * k}</text></g>)}
        {labels.map((l, i) => {
          let acc = 0;
          const gw = bw * 0.6, sw = stacked ? gw : gw / Math.max(1, bars.length);
          return (
            <g key={i}>
              {bars.map((s, j) => { const v = s.data[i]; const x = P.l + i * bw + (bw - gw) / 2 + (stacked ? 0 : j * sw); const yy = stacked ? y(acc + v) : y(v); const hh = stacked ? y(acc) - y(acc + v) : P.t + ih - y(v); acc += v; return <rect key={j} x={x} y={yy} width={Math.max(1, sw - 2)} height={Math.max(0, hh)} rx="2" fill={col(palette, series.indexOf(s))} />; })}
              <text x={P.l + i * bw + bw / 2} y={H - 6} textAnchor="middle" style={axisText}>{l}</text>
            </g>
          );
        })}
        {lines.map((s) => <polyline key={s.name} fill="none" strokeWidth="2" stroke={col(palette, series.indexOf(s))} points={s.data.map((v, i) => `${P.l + i * bw + bw / 2},${y(v)}`).join(" ")} />)}
      </svg>
      {show_legend && series.length > 1 && <Legend items={series.map((s) => s.name)} palette={palette} />}
    </div>
  );
}
