import React from "react";


/** at-layout — page scaffolds: "page" (header + content), "master-detail", "tabset". */
export function Layout({ template = "page", header, master, detail, children, style }) {
  if (template === "master-detail") {
    return (
      <div style={{ display: "flex", flex: 1, minHeight: 0, ...style }}>
        <div style={{ flex: "none", width: 280, borderRight: "1px solid var(--token-border-muted)", overflowY: "auto" }}>{master}</div>
        <div style={{ flex: 1, minWidth: 0, overflowY: "auto" }}>{detail || children}</div>
      </div>
    );
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0, ...style }}>
      {header}
      <div style={{ flex: 1, minHeight: 0, overflowY: "auto", padding: "0 16px 16px", display: "flex", flexDirection: "column", gap: 16 }}>{children}</div>
    </div>
  );
}
