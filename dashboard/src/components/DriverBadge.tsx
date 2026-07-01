export function TeamDot({ color }: { color: string }) {
  return <span className="inline-block h-2.5 w-2.5 rounded-full shrink-0" style={{ background: color }} />
}

export function DriverBadge({ name, team, color }: { name: string; team?: string; color: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <TeamDot color={color} />
      <span className="font-medium text-gray-100">{name}</span>
      {team && <span className="text-xs text-gray-500">{team}</span>}
    </span>
  )
}
