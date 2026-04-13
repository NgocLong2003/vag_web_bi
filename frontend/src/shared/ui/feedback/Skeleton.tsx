interface SkeletonProps {
  className?: string
  width?: string | number
}

export function Skeleton({ className = '', width }: SkeletonProps) {
  return (
    <span
      className={`skeleton ${className}`}
      style={width ? { width: typeof width === 'number' ? `${width}px` : width } : undefined}
    />
  )
}
