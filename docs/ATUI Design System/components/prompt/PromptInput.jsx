import React from "react";
import { Button } from "../actions/Button.jsx";

/** at-prompt-input — multiline composer with send / stop. */
export function PromptInput({ placeholder = "Ask a question…", onSend, busy, onStop }) {
  const [v, setV] = React.useState("");
  const [f, setF] = React.useState(false);
  const send = () => { if (!v.trim()) return; onSend && onSend(v.trim()); setV(""); };
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 8, padding: 8, border: `1px solid ${f ? "var(--token-state-active-accent)" : "var(--token-border-muted)"}`, borderRadius: "var(--token-border-radius-lg)", background: "var(--token-input-background)", boxShadow: f ? "0 0 0 3px color-mix(in srgb, var(--token-state-active-accent) 50%, transparent)" : "none", transition: "border-color 150ms, box-shadow 150ms" }}>
      <textarea rows={1} value={v} placeholder={placeholder} onFocus={() => setF(true)} onBlur={() => setF(false)} onChange={(e) => setV(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
        style={{ flex: 1, resize: "none", border: 0, outline: 0, background: "transparent", fontFamily: "inherit", fontSize: "var(--token-font-size-body)", lineHeight: "20px", padding: "4px", maxHeight: 120 }} />
      {busy ? <Button size="md" type="secondary" icon="stop" title="Stop" onClick={onStop} /> : <Button size="md" icon="send" title="Send" disabled={!v.trim()} onClick={send} />}
    </div>
  );
}
