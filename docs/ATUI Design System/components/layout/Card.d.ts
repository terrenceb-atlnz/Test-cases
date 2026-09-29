import * as React from "react";

/**
 * at-card — surface container with header, content and footer.
 * @startingPoint section="Layout" subtitle="surface container with header, content and footer." viewport="700x300"
 */
export interface CardProps {
  card_title?: string;
  subtitle?: string;
  content?: React.ReactNode;
  header?: React.ReactNode;
  header_actions?: React.ReactNode;
  footer?: React.ReactNode;
  padding?: boolean;
  shadow?: "none"|"sm"|"lg";
  children?: React.ReactNode;
  style?: React.CSSProperties;
  contentStyle?: React.CSSProperties;
}

export declare function Card(props: CardProps): React.ReactElement;
