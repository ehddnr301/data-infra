type HighlightTextProps = {
  text: string
  keyword: string
  className?: string
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function HighlightText({ text, keyword, className }: HighlightTextProps) {
  const normalizedKeyword = keyword.trim()

  if (!normalizedKeyword) {
    return <span className={className}>{text}</span>
  }

  const escaped = escapeRegex(normalizedKeyword)
  const regex = new RegExp(`(${escaped})`, 'gi')
  const parts = text.split(regex)
  let cursor = 0

  return (
    <span className={className}>
      {parts.map((part) => {
        const key = `${part}-${cursor}`
        cursor += part.length
        const isMatch = part.toLowerCase() === normalizedKeyword.toLowerCase()
        if (!isMatch) {
          return <span key={key}>{part}</span>
        }

        return (
          <mark key={key} className="rounded bg-yellow-200 px-0.5 text-current">
            {part}
          </mark>
        )
      })}
    </span>
  )
}
