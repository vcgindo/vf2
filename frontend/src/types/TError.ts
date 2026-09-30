/**
 * Standard error retruend from API
 */
export interface TError {
  status: number
  error: string
  message: string
  path: string
  /** For fields validation (if there is), eg
   * {name: "Name is required", email: ["Email is required", "Minimum length 2"]}
   */
  response: any
  validation?: Record<string, string | string[]>
  code?: string
  traceId?: string
  traceError?: string
  timestamp: Date
  email?: string | string[]
}
