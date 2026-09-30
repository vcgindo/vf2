export interface ChangePassword {
  old_password: string
  new_password: string
}

export interface ChangeStatus {
  user_id: number
  is_active: boolean
}

export interface InfoUser {
  email: string
  name: string
  password: string
  tc: boolean
  roles: number[]
  brands: string[]
  sub_brands: string[]
  categories: string[]
  location_regions: string[]
  location_types: string[]
  location_clusters: string[]
}

export interface ChangeTheme {
  theme_ui: string
}