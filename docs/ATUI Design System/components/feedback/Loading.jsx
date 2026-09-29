import React from "react";

const SPIN = { sm: [16, 1], md: [32, 2], lg: [64, 4] };
const COLOR = { default: "var(--token-text-active)", error: "var(--token-state-error-foreground)", secondary: "var(--token-text-foreground)" };
const FONT = { sm: "var(--token-font-size-sm)", md: "var(--token-font-size-body)", lg: "var(--token-font-size-xl)" };
const KF = "@keyframes at-spin{to{transform:rotate(360deg)}}@keyframes at-bounce-dots{0%,80%,100%{transform:scale(0);opacity:.5}40%{transform:scale(1);opacity:1}}@keyframes at-wave{0%,100%{transform:scaleY(.4);opacity:.5}50%{transform:scaleY(1);opacity:1}}@keyframes at-typing{0%,60%,100%{transform:translateY(0);opacity:.4}30%{transform:translateY(-10px);opacity:1}}";

/** at-loading — spinner / dots / typing / wave indicator. */
export function Loading({ variant = "spinner", type = "default", size = "md", children, style }) {
  const c = COLOR[type];
  let ind;
  if (variant === "spinner") {
    const [px, bw] = SPIN[size];
    ind = <span style={{ display: "inline-block", width: px, height: px, borderRadius: "50%", border: `${bw}px solid ${c}`, borderInlineEndColor: "transparent", animation: "at-spin 1s linear infinite" }}></span>;
  } else {
    const cfg = { dots: [4, 4, "at-bounce-dots", [0, 250, 500]], typing: [4, 4, "at-typing", [0, 250, 500]], wave: [4, 16, "at-wave", [0, 100, 200, 300, 400]] }[variant];
    ind = (
      <span style={{ display: "flex", alignItems: "center", gap: 4, color: c }}>
        {cfg[3].map((d) => <span key={d} style={{ width: cfg[0], height: cfg[1], borderRadius: 999, background: "currentColor", animation: `${cfg[2]} 1s infinite`, animationDelay: d + "ms" }}></span>)}
      </span>
    );
  }
  return (
    <span role="status" aria-label={variant === "typing" ? "Typing" : "Loading"} style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: FONT[size], ...style }}>
      <style>{KF}</style>
      {ind}
      {children}
    </span>
  );
}
