import { get } from '@/utils/http'
import { UserItem } from '@/types'

export function fetchUsers() {
  return get<{ items: UserItem[]; total: number }>('/users/')
}
