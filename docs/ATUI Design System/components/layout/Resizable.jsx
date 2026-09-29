import React from "react";


/** at-resizable-group / -panel / -handle — draggable split between two panels. */
export function Resizable({ direction = "horizontal", initial = 50, min = 15, first, second, style }) {
  const [p, setP] = React.useState(initial);
  const ref = React.useRef();
  const drag = (e) => {
    e.preventDefault();
    const r = ref.current.getBoundingClientRect();
    const mv = (ev) => { const v = direction === "horizontal" ? ((ev.clientX - r.left) / r.width) * 100 : ((ev.clientY - r.top) / r.height) * 100; setP(Math.min(100 - min, Math.max(min, v))); };
    const up = () => { document.removeEventListener("mousemove", mv); document.removeEventListener("mouseup", up); };
    document.addEventListener("mousemove", mv); document.addEventListener("mouseup", up);
  };
  const hz = direction === "horizontal";
  return (
    <div ref={ref} style={{ display: "flex", flexDirection: hz ? "row" : "column", width: "100%", height: "100%", minHeight: 0, ...style }}>
      <div style={{ flexBasis: p + "%", minWidth: 0, minHeight: 0, overflow: "auto" }}>{first}</div>
      <div role="separator" onMouseDown={drag} style={{ flex: "none", [hz ? "width" : "height"]: 1, background: "var(--token-border-muted)", cursor: hz ? "col-resize" : "row-resize", position: "relative" }}>
        <span style={{ position: "absolute", [hz ? "left" : "top"]: -3, [hz ? "width" : "height"]: 7, [hz ? "top" : "left"]: 0, [hz ? "bottom" : "right"]: 0 }}></span>
      </div>
      <div style={{ flex: 1, minWidth: 0, minHeight: 0, overflow: "auto" }}>{second}</div>
    </div>
  );
}
