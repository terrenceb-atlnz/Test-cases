import React from "react";
import { Icon } from "../core/Icon.jsx";
import { Button } from "./Button.jsx";

/** at-reload-button — secondary icon button that spins while refreshing. */
export function ReloadButton({ onClick, label, size = "lg", in_progress }) {
  const [busy, setBusy] = React.useState(false);
  const spin = in_progress ?? busy;
  return (
    <Button type="secondaryOutline" size={size} label={label} title="Reload" onClick={() => { setBusy(true); setTimeout(() => setBusy(false), 900); onClick && onClick(); }}>
      <Icon name="renew" style={{ animation: spin ? "at-spin 1s linear infinite" : "none" }} />
    </Button>
  );
}
