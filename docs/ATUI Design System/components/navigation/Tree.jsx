import React from "react";
import { Icon } from "../core/Icon.jsx";

const hoverBg = "color-mix(in srgb, var(--token-surface-overlay) 10%, transparent)";

function TreeNode({ node, depth, sel, onSelect }) {
  const [open, setOpen] = React.useState(!!node.open);
  const [h, setH] = React.useState(false);
  const kids = node.children && node.children.length;
  const active = sel === node.id;
  return (
    <div role="treeitem" aria-expanded={kids ? open : undefined} aria-selected={active}>
      <div onClick={() => { if (kids) setOpen(!open); onSelect(node.id); }} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
        style={{ display: "flex", alignItems: "center", gap: 4, padding: "4px 8px", paddingLeft: 8 + depth * 16, borderRadius: "var(--token-menu-item-radius)", cursor: "pointer",
          background: active ? "var(--token-state-active-background)" : h ? hoverBg : "transparent", color: active ? "var(--token-state-active-foreground)" : undefined }}>
        <span style={{ width: 16, display: "inline-flex" }}>{kids ? <Icon name="chevron_right" style={{ transform: open ? "rotate(90deg)" : "none", transition: "transform 150ms" }} /> : null}</span>
        {node.icon && <Icon name={node.icon} />}
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.label}</span>
      </div>
      {kids && open ? <div role="group">{node.children.map((c) => <TreeNode key={c.id} node={c} depth={depth + 1} sel={sel} onSelect={onSelect} />)}</div> : null}
    </div>
  );
}

/** at-tree / at-tree-item — hierarchical navigation. data: [{id,label,icon,children}] */
export function Tree({ data = [], selected, onSelect, style }) {
  const [sel, setSel] = React.useState(selected);
  return <div role="tree" style={{ display: "flex", flexDirection: "column", gap: 2, ...style }}>{data.map((n) => <TreeNode key={n.id} node={n} depth={0} sel={sel} onSelect={(id) => { setSel(id); onSelect && onSelect(id); }} />)}</div>;
}
