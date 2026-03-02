export function prettyLineageEdgeLabel(raw: string): string {
  const compact = raw.replace(/\s+/g, ' ').trim()
  if (!compact) {
    return ''
  }

  const bracket = compact.match(/\[([^\]]+)\]/)
  const action = bracket?.[1]?.trim()
  if (action) {
    if (/jsonl/i.test(compact)) {
      return `${action} JSONL`
    }
    if (/d1|database|db/i.test(compact)) {
      return `${action} D1`
    }
    return action
  }

  return compact
}

export function truncateLineageEdgeLabel(label: string, maxChars: number): string {
  if (maxChars <= 0) {
    return ''
  }

  if (label.length <= maxChars) {
    return label
  }

  if (maxChars === 1) {
    return '…'
  }

  return `${label.slice(0, maxChars - 1)}…`
}
