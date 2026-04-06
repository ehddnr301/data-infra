import { apiGet } from '@/lib/api-client'
import type { AiManifestEntry, ApiSuccess } from '@pseudolab/shared-types'

export function getManifest() {
  return apiGet<ApiSuccess<AiManifestEntry[]>>('/ai/manifest')
}
