import React from "react";
import { Icon } from "../core/Icon.jsx";
import { Badge } from "../feedback/Badge.jsx";

/** at-chip-list — removable lg badges. chips: string[] */
export function ChipList({ chips = [], type = "default", removable = true, onChange, style }) {
  const [c, setC] = React.useState(chips);
  React.useEffect(() => setC(chips), [chips.join("|")]);
  const rm = (x) => { const n = c.filter((y) => y !== x); setC(n); onChange && onChange(n); };
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 4, ...style }}>
      {c.map((x) => (
        <Badge key={x} size="lg" type={type} label={x}>
          {removable && <span role="button" aria-label={"Remove " + x} onClick={() => rm(x)} style={{ display: "inline-flex", cursor: "pointer", marginLeft: 2 }}><Icon name="close" size={12} /></span>}
        </Badge>
      ))}
    </div>
  );
}
