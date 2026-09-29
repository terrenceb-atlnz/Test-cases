import React from "react";
import { PromptThread } from "./PromptThread.jsx";
import { PromptInput } from "./PromptInput.jsx";
import { Icon } from "../core/Icon.jsx";

/** at-prompt-container — assistant panel: header, thread, composer. */
export function PromptContainer({ prompt_title = "Assistant", messages: init = [], respond, style }) {
  const [msgs, setMsgs] = React.useState(init);
  const [busy, setBusy] = React.useState(false);
  const send = (t) => {
    setMsgs((m) => [...m, { role: "user", content: t }, { role: "assistant", loading: true }]);
    setBusy(true);
    setTimeout(() => { setMsgs((m) => [...m.slice(0, -1), { role: "assistant", content: respond ? respond(t) : "Here's what I found for “" + t + "”." }]); setBusy(false); }, 1100);
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0, background: "var(--token-surface-foreground)", ...style }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 16px", borderBottom: "1px solid var(--token-border-muted)" }}>
        <Icon name="ai" size={20} style={{ color: "var(--token-state-active-accent)" }} />
        <span style={{ fontSize: "var(--token-font-size-h4)", fontWeight: "var(--token-font-weight-med)" }}>{prompt_title}</span>
      </div>
      <PromptThread messages={msgs} />
      <div style={{ padding: 12 }}><PromptInput busy={busy} onSend={send} onStop={() => setBusy(false)} /></div>
    </div>
  );
}
