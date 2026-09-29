import React from "react";


/** at-status-bar — segmented proportion bar. segments: [{value, color}] color is a CSS var name or colour. */
export function StatusBar({ segments = [], size = "sm", style }) {
  const total = segments.reduce((a, s) => a + s.value, 0) || 1;
  return (
    <div style={{ display: "flex", gap: 2, height: size === "lg" ? 16 : 8, borderRadius: 999, overflow: "hidden", ...style }}>
      {segments.filter((s) => s.value > 0).map((s, i) => <div key={i} title={s.label} style={{ flexBasis: (s.value / total) * 100 + "%", background: s.color.startsWith("--") ? `var(${s.color})` : s.color }}></div>)}
    </div>
  );
}
