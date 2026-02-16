/** YYYY-MM-DD 형식 */
export type IsoDate = string

/** ISO 8601 형식 (예: 2024-01-15T09:30:00Z) */
export type IsoDateTime = string

/** JSON.stringify 결과 문자열 */
export type JsonText = string

/** D1 Row 공통 인제스트 메타데이터 */
export type IngestMeta = {
  created_at: IsoDateTime
  batch_date: IsoDate
}
