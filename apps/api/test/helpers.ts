import { expect } from 'vitest'
import { z } from 'zod'

export const ProblemDetailSchema = z.object({
  type: z.string(),
  title: z.string(),
  status: z.number(),
  detail: z.string().optional(),
  instance: z.string().optional(),
})

export const apiSuccessSchema = <T extends z.ZodTypeAny>(dataSchema: T) =>
  z.object({
    success: z.literal(true),
    data: dataSchema,
    meta: z.record(z.unknown()).optional(),
  })

export const paginatedSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
  z.object({
    success: z.literal(true),
    data: z.array(itemSchema),
    pagination: z.object({
      page: z.number(),
      pageSize: z.number(),
      total: z.number(),
      totalPages: z.number(),
    }),
  })

export const LivenessSchema = z.object({
  status: z.literal('ok'),
  timestamp: z.string(),
})

const BindingCheckSchema = z.object({
  status: z.enum(['ok', 'fail']),
  latencyMs: z.number().optional(),
})

export const ReadinessSchema = z.object({
  status: z.enum(['ok', 'degraded', 'unhealthy']),
  timestamp: z.string(),
  checks: z.object({
    d1: BindingCheckSchema,
    r2: BindingCheckSchema,
    kv: BindingCheckSchema,
  }),
})

export function expectJson(res: Response): void {
  expect(res.headers.get('content-type')).toContain('application/json')
}

export function expectProblemJson(res: Response): void {
  expect(res.headers.get('content-type')).toContain('application/problem+json')
}
