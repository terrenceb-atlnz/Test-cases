import React from "react";

/** at-card — surface container: header (title/subtitle/actions), content, footer. */
export function Card({ card_title, subtitle, content, header, header_actions, footer, padding = true, shadow = "none", children, style, contentStyle }) {
  const sh = { none: "none", sm: "var(--token-shadow-sm)", lg: "var(--token-shadow-lg)" }[shadow];
  const hasHeader = header || card_title || subtitle || header_actions;
  return (
    <div style={{ position: "relative", display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--token-card-background)", border: "1px solid var(--token-card-border)", borderRadius: "var(--token-card-radius)", boxShadow: sh, ...style }}>
      {hasHeader && (
        <div style={{ position: "relative", display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 8, padding: 16 }}>
          {header}
          {(card_title || subtitle) && (
            <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
              {card_title && <h4 style={{ fontSize: "var(--token-font-size-h4)", fontWeight: "var(--token-font-weight-med)" }}>{card_title}</h4>}
              {subtitle && <h5 style={{ fontSize: "var(--token-font-size-sm)", fontWeight: "var(--token-font-weight-light)", color: "var(--token-text-muted)" }}>{subtitle}</h5>}
            </div>
          )}
          {header_actions}
        </div>
      )}
      <div style={{ position: "relative", display: "flex", flexDirection: "column", flex: "1 1 auto", minHeight: 0, padding: padding ? (hasHeader ? "8px 16px 16px" : 16) : 0, ...contentStyle }}>
        {content}
        {children}
      </div>
      {footer && <div style={{ padding: 16 }}>{footer}</div>}
    </div>
  );
}
