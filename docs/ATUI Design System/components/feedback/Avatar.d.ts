import * as React from "react";

/**
 * at-avatar — decorative initials/image circle.
 */
export interface AvatarProps {
  src?: string;
  alt?: string;
  initials?: string;
  size?: "sm"|"md"|"lg";
  variant?: "primary"|"secondary"|"muted";
}

export declare function Avatar(props: AvatarProps): React.ReactElement;
