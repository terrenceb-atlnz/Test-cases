import React from "react";
import { PromptMessage } from "./PromptMessage.jsx";

/** at-prompt-thread — scrolling list of PromptMessages. */
export function PromptThread({ messages = [], style }) {
  const ref = React.useRef();
  React.useEffect(() => { if (ref.current) ref.current.scrollTop = ref.current.scrollHeight; }, [messages.length]);
  return <div ref={ref} style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 16, padding: 16, ...style }}>{messages.map((m, i) => <PromptMessage key={i} {...m} />)}</div>;
}
