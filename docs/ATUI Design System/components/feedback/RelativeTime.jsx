import React from "react";


function rel(d) {
  const s = Math.round((Date.now() - new Date(d).getTime()) / 1000);
  if (s < 60) return "Just now";
  const m = Math.round(s / 60); if (m < 60) return m + (m === 1 ? " minute ago" : " minutes ago");
  const h = Math.round(m / 60); if (h < 24) return h + (h === 1 ? " hour ago" : " hours ago");
  const dd = Math.round(h / 24); return dd + (dd === 1 ? " day ago" : " days ago");
}

/** at-relative-time — humanised timestamp with absolute time in the tooltip. */
export function RelativeTime({ date, style }) {
  return <time dateTime={new Date(date).toISOString()} title={new Date(date).toLocaleString()} style={{ color: "inherit", ...style }}>{rel(date)}</time>;
}
