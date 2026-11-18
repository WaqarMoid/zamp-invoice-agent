import React from "react";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
  width?: string | number;
  height?: string | number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = "",
  width,
  height,
  style,
  ...props
}) => {
  return (
    <div
      style={{ width, height, ...style }}
      className={`bg-[var(--line)] rounded-[6px] animate-pulse duration-1000 ${className}`}
      {...props}
    />
  );
};
