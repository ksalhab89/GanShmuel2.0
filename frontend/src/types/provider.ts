/**
 * Type definitions for Provider Registration Service
 */

export type CandidateStatus = 'pending' | 'approved' | 'rejected'
export type ProductType = 'apples' | 'oranges' | 'grapes' | 'cherries'

/**
 * Candidate registration data
 */
export interface CandidateCreate {
  company_name: string
  contact_email: string
  phone: string
  products: ProductType[]
  truck_count: number
  capacity_tons_per_day: number
  location: string
  additional_notes?: string
}

/**
 * Candidate entity from API
 */
export interface Candidate {
  candidate_id: string  // UUID
  status: CandidateStatus
  company_name: string
  contact_email: string
  phone: string | null
  products: string[]
  truck_count: number
  capacity_tons_per_day: number
  location: string | null
  created_at: string
  provider_id: number | null
}

/**
 * Candidate approval data
 */
export interface CandidateApproval {
  approved: boolean
  rejection_reason?: string
}

/**
 * Candidate list query parameters
 */
export interface CandidateListParams {
  status?: CandidateStatus
  product?: ProductType
  page?: number
  page_size?: number
}

/**
 * Paginated candidate list response
 */
export interface CandidateListResponse {
  candidates: Candidate[]
  pagination: {
    total: number
    limit: number
    offset: number
  }
}

/**
 * API error response
 */
export interface ApiError {
  detail: string
}
