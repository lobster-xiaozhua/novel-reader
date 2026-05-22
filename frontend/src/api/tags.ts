import { get, post, del } from '@/utils/http'

export interface TagItem {
  id: number
  name: string
  color: string
  book_count: number
}

export function fetchTags() {
  return get<{ items: TagItem[]; total: number }>('/tags/')
}

export function createTag(data: { name: string; color: string }) {
  return post<TagItem>('/tags/', data)
}

export function deleteTag(id: number) {
  return del<void>(`/tags/${id}/`)
}
