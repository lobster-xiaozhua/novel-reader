import { useEffect } from 'react'

const SITE_NAME = '小说阅读器'

export function usePageTitle(title: string) {
  useEffect(() => {
    document.title = title ? `${title} - ${SITE_NAME}` : SITE_NAME
  }, [title])
}
