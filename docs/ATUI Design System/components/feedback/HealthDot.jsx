import React from "react";

const PX = { sm: 10, md: 16, lg: 24 };
const LABEL = { good: "Healthy", warn: "Warning", bad: "Critical" };

/** at-health-dot — shape + colour health glyph (circle good, triangle warn, diamond bad). */
export function HealthDot({ status = "good", size = "md", style }) {
  const d = PX[size] || size;
  let g;
  if (status === "bad") g = <svg width={d} height={d} viewBox="0 0 15 15" aria-hidden="true"><path d="M6.37883 0.293045C6.76935 -0.0974796 7.40252 -0.09748 7.79304 0.293044L13.8788 6.37883C14.2694 6.76935 14.2694 7.40252 13.8788 7.79304L7.79305 13.8788C7.40252 14.2694 6.76935 14.2694 6.37883 13.8788L0.293045 7.79305C-0.0974796 7.40252 -0.09748 6.76935 0.293044 6.37883L6.37883 0.293045Z" fill="var(--chart-alert-3, #ff5252)" stroke="var(--chart-alert-3, #ff5252)" strokeWidth="1" strokeLinejoin="round"></path></svg>;
  else if (status === "warn") g = <svg width={d} height={d} viewBox="0 0 15 15" aria-hidden="true"><path d="M6.81445 2.38965C7.19935 1.72298 8.16197 1.72298 8.54688 2.38965L14.1533 12.1006C14.5382 12.7673 14.0569 13.6006 13.2871 13.6006H2.07422C1.30442 13.6006 0.823108 12.7673 1.20801 12.1006L6.81445 2.38965Z" fill="var(--chart-alert-2, #f59f00)" stroke="var(--chart-alert-2, #f59f00)" strokeWidth="1" strokeLinejoin="round"></path></svg>;
  else g = <svg width={d} height={d} viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="7" fill="var(--chart-alert-1, #4caf50)"></circle></svg>;
  return <span role="img" aria-label={LABEL[status]} style={{ display: "inline-flex", alignItems: "center", ...style }}>{g}</span>;
}
