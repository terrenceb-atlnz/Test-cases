import React from "react";


/** at-dashboard — responsive widget grid. Children may set data-span (columns). */
export function Dashboard({ columns = 12, gap = 16, children, style }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`, gap, ...style }}>
      {React.Children.map(children, (c) => c && <div style={{ gridColumn: `span ${c.props.span || 4}`, minWidth: 0, display: "flex", flexDirection: "column" }}>{c}</div>)}
    </div>
  );
}
