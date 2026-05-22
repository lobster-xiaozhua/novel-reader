import { get } from '@/utils/http'

export interface UserItem {
  id: number
  username: string
  email: string
  is_staff: boolean
  date_joined: string
  last_login?: string
  book_count: number
}

export function fetchUsers() {
  return get<{ items: UserItem[]; total: number }>('/users/')
}
