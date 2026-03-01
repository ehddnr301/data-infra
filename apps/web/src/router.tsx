import { HomePage } from '@/routes'
import { RootErrorComponent, RootNotFoundComponent, RootRouteComponent } from '@/routes/__root'
import { AboutPage } from '@/routes/about'
import { DatasetsPage } from '@/routes/datasets'
import { DatasetDetailPage } from '@/routes/datasets/$datasetId'
import { GlossaryListPage } from '@/routes/glossary'
import { GlossaryDetailPage } from '@/routes/glossary/$termId'
import { GlossaryFormPage } from '@/routes/glossary/form'
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

const datasetsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/datasets',
  component: DatasetsPage,
})

const datasetDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/datasets/$datasetId',
  component: DatasetDetailPage,
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

const routeTree = rootRoute.addChildren([
  indexRoute,
  aboutRoute,
  datasetsRoute,
  datasetDetailRoute,
  glossaryRoute,
  glossaryNewRoute,
  glossaryDetailRoute,
  glossaryEditRoute,
  searchRoute,
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
