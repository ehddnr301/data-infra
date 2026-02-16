import type { IsoDate } from './scalars'

export type PaginationParams = {
  page?: number
  pageSize?: number
}

export type DateRangeParams = {
  from?: IsoDate
  to?: IsoDate
}

export type SortParams<F extends string = string> = {
  sortBy?: F
  order?: 'asc' | 'desc'
}
