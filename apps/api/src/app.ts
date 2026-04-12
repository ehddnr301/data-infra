import type { Env } from '@pseudolab/shared-types'
import { Hono } from 'hono'
import { corsMiddleware } from './middleware/cors'
import { errorHandler, notFoundHandler } from './middleware/error-handler'
import { loggerMiddleware } from './middleware/logger'
import aiRouter from './routes/ai'
import authRouter from './routes/auth'
import catalogRouter from './routes/catalog'
import commentsRouter from './routes/comments'
import discordRouter from './routes/discord'
import githubRouter from './routes/github'
import healthRouter from './routes/health'
import marketplaceRouter from './routes/marketplace'
import queryRouter from './routes/query'
import searchRouter from './routes/search'

const app = new Hono<{ Bindings: Env }>().basePath('/api')

app.use('*', corsMiddleware)
app.use('*', loggerMiddleware)

app.route('/auth', authRouter)
app.route('/health', healthRouter)
app.route('/github', githubRouter)
app.route('/catalog', catalogRouter)
app.route('/marketplace', marketplaceRouter)
app.route('/discord', discordRouter)
app.route('/search', searchRouter)
app.route('/ai', aiRouter)
app.route('/query', queryRouter)
app.route('/datasets', commentsRouter)

app.onError(errorHandler)
app.notFound(notFoundHandler)

export default app
