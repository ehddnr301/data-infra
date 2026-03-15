import { router } from '@/router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'

vi.mock('@/hooks/use-marketplace', () => ({
  useListings: () => ({ isPending: false, isError: false, data: { data: [] } }),
  useMarketplaceDomains: () => ({
    isPending: false,
    isError: false,
    data: {
      data: [
        { key: 'github', listing_count: 1 },
        { key: 'discord', listing_count: 1 },
      ],
    },
  }),
}))

test('renders marketplace header', async () => {
  const queryClient = new QueryClient()
  const history = createMemoryHistory({ initialEntries: ['/'] })
  router.update({ history })

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )

  expect(await screen.findByText('PseudoLab Data Marketplace')).toBeInTheDocument()
  const listingLinks = await screen.findAllByRole('link', { name: /리스팅/ })
  expect(listingLinks.length).toBeGreaterThan(0)
})
