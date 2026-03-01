import { HighlightText } from '@/components/search/highlight-text'
import { render, screen } from '@testing-library/react'

describe('HighlightText', () => {
  it('highlights text case-insensitively', () => {
    render(<HighlightText text="GitHub Dataset" keyword="github" />)

    const mark = screen.getByText('GitHub')
    expect(mark.tagName.toLowerCase()).toBe('mark')
  })

  it('renders plain text for empty keyword', () => {
    render(<HighlightText text="Plain text" keyword="" />)
    expect(screen.getByText('Plain text')).toBeInTheDocument()
    expect(document.querySelector('mark')).toBeNull()
  })

  it('escapes regex-special keyword characters', () => {
    render(<HighlightText text="a.+*?()[]b" keyword=".+*?()[]" />)

    const mark = screen.getByText('.+*?()[]')
    expect(mark.tagName.toLowerCase()).toBe('mark')
  })
})
