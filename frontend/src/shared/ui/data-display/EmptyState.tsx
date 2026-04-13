import { FileX } from 'lucide-react'

interface EmptyStateProps {
  message?: string
  icon?: typeof FileX
}

export function EmptyState({ message = 'Chưa có dữ liệu', icon: Icon = FileX }: EmptyStateProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-surface-4">
      <Icon className="h-10 w-10 opacity-40" />
      <p className="text-sm">{message}</p>
    </div>
  )
}
