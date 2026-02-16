import type { HTMLAttributes } from 'react'

export function Tooltip({ title, children }: HTMLAttributes<HTMLElement>) {
  return <span title={typeof title === 'string' ? title : undefined}>{children}</span>
}
