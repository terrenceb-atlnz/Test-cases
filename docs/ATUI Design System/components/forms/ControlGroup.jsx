import React from "react";


/** at-control-group — joins adjacent inputs/buttons into one bordered control (shared radii). */
export function ControlGroup({ children, style }) {
  const items = React.Children.toArray(children);
  return (
    <div style={{ display: "inline-flex", alignItems: "stretch", ...style }}>
      {items.map((c, i) => (
        <div key={i} style={{ marginLeft: i ? -1 : 0, display: "flex", borderRadius: i === 0 ? "var(--token-input-radius) 0 0 var(--token-input-radius)" : i === items.length - 1 ? "0 var(--token-input-radius) var(--token-input-radius) 0" : 0, overflow: "hidden" }}>{c}</div>
      ))}
    </div>
  );
}
