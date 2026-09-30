export interface RegisterRequest {
  name: string
  email: string
  password: string
  password2: string
  tc: boolean
}
export interface LoginRequest {
  email: string
  password: string
}
export interface ChangePassRequest {
  uid: string
  token: string
  new_password: string
  confirm_password: string
}

export interface User {
  id: number
  email: string
  role?: string
  is_admin: boolean
  name: string
}
