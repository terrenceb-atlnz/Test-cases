import React from "react";


/** at-dialog — modal over a 20% black backdrop; slot an at-card inside. */
export function Dialog({ open, onClose, close_backdrop = false, close_esc = true, backdrop = true, children, width = "var(--token-width-panel-sm)", aria_label }) {
  React.useEffect(() => {
    if (!open || !close_esc) return;
    const k = (e) => e.key === "Escape" && onClose && onClose("esc");
    document.addEventListener("keydown", k);
    return () => document.removeEventListener("keydown", k);
  }, [open, close_esc]);
  if (!open) return null;
  return (
    <div role="dialog" aria-modal="true" aria-label={aria_label} onMouseDown={(e) => close_backdrop && e.target === e.currentTarget && onClose && onClose("backdrop")}
      style={{ position: "fixed", inset: 0, zIndex: "var(--token-z-index-modal)", display: "flex", alignItems: "center", justifyContent: "center", background: backdrop ? "rgba(0,0,0,0.2)" : "transparent", animation: "fadeIn .15s ease" }}>
      <div style={{ width, maxWidth: "calc(100vw - 32px)", boxShadow: "var(--token-shadow-3)", borderRadius: "var(--token-card-radius)", animation: "animInUp .15s ease" }}>{children}</div>
    </div>
  );
}
