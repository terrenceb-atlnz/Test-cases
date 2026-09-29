import React from "react";


/** at-avatar — initials or image in a circle. */
export function Avatar({ src, alt, initials, size = "md", variant = "secondary" }) {
  const d = { sm: [24, "var(--token-font-size-xs)"], md: [32, "var(--token-font-size-sm)"], lg: [40, "var(--token-font-size-body)"] }[size];
  const c = { primary: ["var(--token-surface-inv)", "var(--token-text-inv)"], secondary: ["var(--token-state-active-background)", "var(--token-state-active-foreground)"], muted: ["var(--token-surface-0)", "var(--token-text-secondary)"] }[variant];
  return (
    <span style={{ display: "inline-flex", flex: "none", alignItems: "center", justifyContent: "center", overflow: "hidden", borderRadius: 999, width: d[0], height: d[0], fontSize: d[1], fontWeight: "var(--token-font-weight-med)", userSelect: "none", background: c[0], color: c[1] }}>
      {src ? <img src={src} alt={alt || "Avatar"} style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : initials}
    </span>
  );
}
