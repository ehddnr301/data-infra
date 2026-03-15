import { HomePage } from '@/routes'
import { RootErrorComponent, RootNotFoundComponent, RootRouteComponent } from '@/routes/__root'
import { AboutPage } from '@/routes/about'
import { DomainDetailPage } from '@/routes/domains/$domainKey'
import { GlossaryListPage } from '@/routes/glossary'
import { GlossaryDetailPage } from '@/routes/glossary/$termId'
import { GlossaryFormPage } from '@/routes/glossary/form'
import { ListingsPage } from '@/routes/listings'
import { ListingDetailPage } from '@/routes/listings/$domain/$listingSlug'
import { SearchPage } from '@/routes/search'
import { createRootRoute, createRoute, createRouter } from '@tanstack/react-router'

const rootRoute = createRootRoute({
  component: RootRouteComponent,
  errorComponent: RootErrorComponent,
  notFoundComponent: RootNotFoundComponent,
})

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: HomePage,
})

const aboutRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/about',
  component: AboutPage,
})

const glossaryRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/glossary',
  component: GlossaryListPage,
})

const glossaryNewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/glossary/new',
  component: GlossaryFormPage,
})

const glossaryDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/glossary/$termId',
  component: GlossaryDetailPage,
})

const glossaryEditRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/glossary/$termId/edit',
  component: GlossaryFormPage,
})

const searchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/search',
  component: SearchPage,
})

const listingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/listings',
  component: ListingsPage,
})

const listingDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/listings/$domain/$listingSlug',
  component: ListingDetailPage,
})

const domainDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/domains/$domainKey',
  component: DomainDetailPage,
})

const routeTree = rootRoute.addChildren([
  indexRoute,
  aboutRoute,
  glossaryRoute,
  glossaryNewRoute,
  glossaryDetailRoute,
  glossaryEditRoute,
  searchRoute,
  listingsRoute,
  listingDetailRoute,
  domainDetailRoute,
])

export const router = createRouter({
  routeTree,
  defaultPreload: 'intent',
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
