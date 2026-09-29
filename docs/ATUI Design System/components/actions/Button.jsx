import React from "react";
import { Icon } from "../core/Icon.jsx";
import { Loading } from "../feedback/Loading.jsx";

const mix = (v, p) => `color-mix(in srgb, var(${v}) ${p}%, transparent)`;
const SIZE = {
  sm: { height: "var(--token-button-height-sm)", padding: "0 var(--token-button-px-sm)" },
  md: { height: "var(--token-button-height-md)", padding: "0 var(--token-button-px-md)" },
  lg: { height: "var(--token-button-height-lg)", padding: "0 var(--token-button-px-lg)" },
};
const TYPE = {
  primary: { background: "var(--token-state-active-accent)", color: "var(--token-button-foreground-inv)", hover: mix("--token-surface-overlay", 30), active: mix("--token-state-active-accent", 70) },
  primaryOutline: { border: "1px solid var(--token-state-active-accent)", color: "var(--token-state-active-accent)", hover: mix("--token-state-active-accent", 10), active: mix("--token-state-active-accent", 20) },
  primaryText: { color: "var(--token-state-active-accent)", hover: mix("--token-state-active-accent", 10), active: mix("--token-state-active-accent", 20) },
  secondary: { background: "var(--token-surface-2)", color: "var(--token-text-foreground)", hover: mix("--token-surface-overlay", 10), active: mix("--token-surface-overlay", 16) },
  secondaryOutline: { border: "1px solid var(--token-text-muted)", color: "var(--token-text-foreground)", hover: mix("--token-surface-overlay", 10), active: mix("--token-surface-overlay", 16) },
  secondaryText: { color: "var(--token-text-foreground)", hover: mix("--token-surface-overlay", 10), active: mix("--token-surface-overlay", 16) },
  destructive: { background: "var(--token-state-error-accent)", color: "var(--token-button-foreground-inv)", hover: mix("--token-surface-overlay", 30), active: mix("--token-state-error-accent", 70), glow: "--token-state-error-accent" },
  destructiveOutline: { border: "1px solid var(--token-state-error-accent)", color: "var(--token-state-error-accent)", hover: mix("--token-state-error-accent", 10), active: mix("--token-state-error-accent", 20), glow: "--token-state-error-accent" },
  destructiveText: { color: "var(--token-state-error-accent)", hover: mix("--token-state-error-accent", 10), active: mix("--token-state-error-accent", 20), glow: "--token-state-error-accent" },
};

/** at-button — ATUI's button primitive. */
export function Button({ label, type = "primary", size = "lg", disabled = false, in_progress = false, icon, icon_after, onClick, children, style, title, submit }) {
  const [hover, setHover] = React.useState(false);
  const [press, setPress] = React.useState(false);
  const [focus, setFocus] = React.useState(false);
  const t = TYPE[type] || TYPE.primary;
  const iconOnly = icon && !label && !children;
  const spinner = type === "primary" || type === "destructive" ? "default" : type.startsWith("destructive") ? "error" : "secondary";
  return (
    <span
      role="button" tabIndex={disabled ? -1 : 0} aria-disabled={disabled || undefined} title={title}
      onClick={(e) => !disabled && onClick && onClick(e)}
      onKeyDown={(e) => { if (!disabled && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); onClick && onClick(e); } }}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => { setHover(false); setPress(false); }}
      onMouseDown={() => setPress(true)} onMouseUp={() => setPress(false)}
      onFocus={(e) => setFocus(e.target.matches(":focus-visible"))} onBlur={() => setFocus(false)}
      style={{
        position: "relative", boxSizing: "border-box", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 4,
        overflow: "hidden", borderRadius: "var(--token-button-radius)", fontWeight: "var(--token-font-weight-med)", fontSize: "var(--token-font-size-button)",
        whiteSpace: "nowrap", cursor: "pointer", userSelect: "none", outline: "none", border: t.border || "none", background: t.background || "transparent",
        color: t.color, transition: "color 150ms ease-in-out, background-color 150ms ease-in-out, border-color 150ms ease-in-out, box-shadow 150ms ease-in-out",
        boxShadow: focus ? `0 0 0 3px ${mix(t.glow || "--token-state-active-accent", 50)}` : "none",
        ...SIZE[size], ...(iconOnly ? { padding: 0, aspectRatio: "1" } : null),
        ...(disabled ? { pointerEvents: "none", opacity: 0.3, filter: "grayscale(1)" } : null), ...style,
      }}
    >
      <span style={{ position: "relative", zIndex: 2, display: "flex", alignItems: "center", justifyContent: "center", gap: 4, width: "100%", height: "100%" }}>
        {in_progress && <Loading size="sm" type={spinner} style={{ position: "absolute" }} />}
        {!in_progress && icon && <Icon name={icon} />}
        {label && <span style={{ lineHeight: "16px", visibility: in_progress ? "hidden" : "visible" }}>{label}</span>}
        {children}
        {!in_progress && icon_after && <Icon name={icon_after} />}
      </span>
      <span aria-hidden="true" style={{ position: "absolute", inset: 0, zIndex: 1, pointerEvents: "none", transition: "background-color 150ms ease-in-out", background: press ? t.active : hover ? t.hover : "transparent" }}></span>
    </span>
  );
}
