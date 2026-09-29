import * as React from "react";

/**
 * at-table / at-search-table — data grid with sort, selection, row menu, pagination and cell renderers.
 * @startingPoint section="Data" subtitle="data grid with sort, selection, row menu, pagination and cell renderers." viewport="700x300"
 */
export interface TableProps {
  columns: { field: string;
  header: string;
  width?: number;
  sortable?: boolean;
  cell?: string | ((value: any, row: any) => React.ReactNode);
  sortValue?: (row: any) => any }[];
  rows: any[];
  selectable?: boolean;
  onRowClick?: (row: any) => void;
  row_actions?: (row: any) => any[];
  sort?: { field: string;
  dir: "asc"|"desc" };
  empty?: React.ReactNode;
  page_size?: number;
  paginate?: boolean;
  style?: React.CSSProperties;
}

export declare function Table(props: TableProps): React.ReactElement;
