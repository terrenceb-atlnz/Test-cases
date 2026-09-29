import React from "react";

const BG = "var(--token-surface-overlay)";

/** at-tooltip — dark overlay bubble on hover/focus. */
export function Tooltip({ content, position = "top", children, style }) {
  const [open, setOpen] = React.useState(false);
  const pos = {
    top: { bottom: "calc(100% + 6px)", left: "50%", transform: "translateX(-50%)" },
    bottom: { top: "calc(100% + 6px)", left: "50%", transform: "translateX(-50%)" },
    left: { right: "calc(100% + 6px)", top: "50%", transform: "translateY(-50%)" },
    right: { left: "calc(100% + 6px)", top: "50%", transform: "translateY(-50%)" },
  }[position];
  return (
    <span style={{ position: "relative", display: "inline-flex", ...style }} onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}>
      {children}
      {open && (
        <span role="tooltip" style={{ position: "absolute", zIndex: "var(--token-z-index-menu)", ...pos, background: BG, color: "var(--token-text-inv)", fontSize: "var(--token-font-size-sm)", fontWeight: "var(--token-font-weight-light)", lineHeight: "var(--token-line-height-base)", padding: "4px 8px", borderRadius: "var(--token-border-radius-md)", whiteSpace: "nowrap", maxWidth: 300, boxShadow: "var(--token-shadow-2)", pointerEvents: "none", animation: "fadeIn .15s ease-in" }}>
          {content}
        </span>
      )}
    </span>
  );
}
