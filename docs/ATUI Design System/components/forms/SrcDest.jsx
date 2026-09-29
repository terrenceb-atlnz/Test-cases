import React from "react";
import { Icon } from "../core/Icon.jsx";

/** at-src-dest — source → destination pair (e.g. IP/port flows). */
export function SrcDest({ src, dest, src_label = "Source", dest_label = "Destination", style }) {
  const cell = (l, v) => (
    <div style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
      <span style={{ color: "var(--token-text-muted)", fontSize: "var(--token-font-size-xs)" }}>{l}</span>
      <span style={{ fontFamily: "var(--token-font-family-mono)", fontSize: "var(--token-font-size-sm)", overflow: "hidden", textOverflow: "ellipsis" }}>{v}</span>
    </div>
  );
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 12, ...style }}>
      {cell(src_label, src)}
      <Icon name="arrow_right" style={{ color: "var(--token-text-muted)" }} />
      {cell(dest_label, dest)}
    </div>
  );
}
