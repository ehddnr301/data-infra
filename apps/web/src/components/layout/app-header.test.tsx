import { router } from '@/router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'

test('renders catalog header', async () => {
  const queryClient = new QueryClient()
  const history = createMemoryHistory({ initialEntries: ['/'] })
  router.update({ history })

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )

  expect(await screen.findByText('PseudoLab Data Catalog')).toBeInTheDocument()
})
