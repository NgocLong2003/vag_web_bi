type Status = 'ok' | 'busy' | 'error' | 'idle'

interface StatusChipProps {
  status: Status
  text: string
}

const dotClass: Record<Status, string> = {
  ok: 'bg-emerald-500',
  busy: 'bg-amber-500 animate-pulse',
  error: 'bg-red-500',
  idle: 'bg-surface-3',
}

export function StatusChip({ status, text }: StatusChipProps) {
  return (
    <div className="flex h-6 items-center gap-1.5 rounded-full border border-surface-2 bg-surface-1 px-2.5 font-mono text-2xs text-surface-5">
      <span className={`h-[5px] w-[5px] rounded-full ${dotClass[status]}`} />
      {text}
    </div>
  )
}
