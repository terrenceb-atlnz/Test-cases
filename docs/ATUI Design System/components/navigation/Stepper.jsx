import React from "react";
import { Icon } from "../core/Icon.jsx";

/** at-stepper / at-stepper-item — wizard progress. steps: [{title, subtitle}] */
export function Stepper({ steps = [], current = 0, layout = "horizontal", onStepClick, style }) {
  const vert = layout === "vertical";
  return (
    <ol style={{ display: "flex", flexDirection: vert ? "column" : "row", gap: vert ? 0 : 8, listStyle: "none", margin: 0, padding: 0, ...style }}>
      {steps.map((s, i) => {
        const state = i < current ? "complete" : i === current ? "active" : "pending";
        const dot = state === "pending" ? { background: "var(--token-surface-foreground)", border: "1px solid var(--token-border-default)", color: "var(--token-text-muted)" } : { background: "var(--token-state-active-accent)", border: "1px solid var(--token-state-active-accent)", color: "var(--token-button-foreground-inv)" };
        return (
          <li key={i} onClick={() => onStepClick && i <= current && onStepClick(i)} style={{ display: "flex", flexDirection: vert ? "row" : "row", alignItems: vert ? "flex-start" : "center", gap: 8, flex: vert ? "none" : 1, cursor: onStepClick && i <= current ? "pointer" : "default", minWidth: 0, paddingBottom: vert ? 16 : 0 }}>
            <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: 24, height: 24, flex: "none", borderRadius: 999, fontSize: "var(--token-font-size-xs)", fontWeight: "var(--token-font-weight-med)", ...dot }}>
              {state === "complete" ? <Icon name="checkmark" size={14} /> : i + 1}
            </span>
            <span style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
              <span style={{ fontWeight: "var(--token-font-weight-med)", color: state === "pending" ? "var(--token-text-muted)" : "var(--token-text-foreground)", whiteSpace: "nowrap" }}>{s.title}</span>
              {s.subtitle && <span style={{ fontSize: "var(--token-font-size-xs)", color: "var(--token-text-muted)" }}>{s.subtitle}</span>}
            </span>
            {!vert && i < steps.length - 1 && <span style={{ flex: 1, height: 1, minWidth: 16, background: i < current ? "var(--token-state-active-accent)" : "var(--token-border-muted)" }}></span>}
          </li>
        );
      })}
    </ol>
  );
}
