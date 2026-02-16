import { HomePage } from '@/routes'
import { RootErrorComponent, RootNotFoundComponent, RootRouteComponent } from '@/routes/__root'
import { AboutPage } from '@/routes/about'
import { DatasetsPage } from '@/routes/datasets'
import { DatasetDetailPage } from '@/routes/datasets/$datasetId'
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
  component: () => (
    <p className="text-sm text-[var(--muted-foreground)]">용어집은 준비 중입니다.</p>
  ),
})

const routeTree = rootRoute.addChildren([
  indexRoute,
  aboutRoute,
  datasetsRoute,
  datasetDetailRoute,
  glossaryRoute,
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
