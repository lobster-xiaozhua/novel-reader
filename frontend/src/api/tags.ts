import { get, post, del } from '@/utils/http'
import { TagItem } from '@/types'

export function fetchTags() {
  return get<{ items: TagItem[]; total: number }>('/tags/')
}

export function createTag(data: { name: string; color: string }) {
  return post<TagItem>('/tags/', data)
}

export function deleteTag(id: number) {
  return del<void>(`/tags/${id}/`)
}
