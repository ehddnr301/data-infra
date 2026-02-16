import type { Env } from '@pseudolab/shared-types'
import { Hono } from 'hono'
import { corsMiddleware } from './middleware/cors'
import { errorHandler, notFoundHandler } from './middleware/error-handler'
import { loggerMiddleware } from './middleware/logger'
import catalogRouter from './routes/catalog'
import githubRouter from './routes/github'
import healthRouter from './routes/health'

const app = new Hono<{ Bindings: Env }>().basePath('/api')

app.use('*', corsMiddleware)
app.use('*', loggerMiddleware)

app.route('/health', healthRouter)
app.route('/github', githubRouter)
app.route('/catalog', catalogRouter)

app.onError(errorHandler)
app.notFound(notFoundHandler)

export default app
