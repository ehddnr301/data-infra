import { HomePage } from '@/routes'
import { RootErrorComponent, RootNotFoundComponent, RootRouteComponent } from '@/routes/__root'
import { AboutPage } from '@/routes/about'
import { AuthCallbackPage } from '@/routes/auth/callback'
import { DiscussionsListPage } from '@/routes/discussions'
import { DiscussionDetailPage } from '@/routes/discussions/$discussionId'
import { DomainDetailPage } from '@/routes/domains/$domainKey'
import { GlossaryListPage } from '@/routes/glossary'
import { GlossaryDetailPage } from '@/routes/glossary/$termId'
import { GlossaryFormPage } from '@/routes/glossary/form'
import { ListingsPage } from '@/routes/listings'
import { ListingDetailPage } from '@/routes/listings/$domain/$listingSlug'
import { QueryDashboardPage } from '@/routes/query'
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

const queryRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/query',
  component: QueryDashboardPage,
})

const domainDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/domains/$domainKey',
  component: DomainDetailPage,
})

const authCallbackRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/auth/callback',
  component: AuthCallbackPage,
})

const discussionsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/discussions',
  component: DiscussionsListPage,
})

const discussionDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/discussions/$discussionId',
  component: DiscussionDetailPage,
})

const routeTree = rootRoute.addChildren([
  indexRoute,
  aboutRoute,
  authCallbackRoute,
  glossaryRoute,
  glossaryNewRoute,
  glossaryDetailRoute,
  glossaryEditRoute,
  searchRoute,
  queryRoute,
  listingsRoute,
  listingDetailRoute,
  domainDetailRoute,
  discussionsRoute,
  discussionDetailRoute,
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
