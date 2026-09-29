import React from "react";
import { Button } from "../actions/Button.jsx";
import { Loading } from "../feedback/Loading.jsx";

/** at-prompt-message — chat bubble. role "user" = right-aligned surface-1 bubble; "assistant" = plain text with feedback actions. */
export function PromptMessage({ role = "assistant", content, loading, show_actions = true, children }) {
  const [fb, setFb] = React.useState(null);
  const me = role === "user";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: me ? "flex-end" : "flex-start", gap: 4 }}>
      <div style={{ maxWidth: me ? "80%" : "100%", padding: me ? "8px 12px" : 0, borderRadius: "var(--token-message-radius)", background: me ? "var(--token-surface-1)" : "transparent", lineHeight: "var(--token-line-height-richtext)", whiteSpace: "pre-wrap" }}>
        {loading ? <Loading variant="typing" size="sm" /> : content}
        {children}
      </div>
      {!me && !loading && show_actions && (
        <div style={{ display: "flex", gap: 2 }}>
          <Button size="sm" type="secondaryText" icon="copy" title="Copy" />
          <Button size="sm" type="secondaryText" icon={fb === "up" ? "thumbs_up_filled" : "thumbs_up"} title="Good response" onClick={() => setFb("up")} />
          <Button size="sm" type="secondaryText" icon={fb === "down" ? "thumbs_down_filled" : "thumbs_down"} title="Bad response" onClick={() => setFb("down")} />
        </div>
      )}
    </div>
  );
}
