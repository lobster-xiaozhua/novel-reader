import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { useAppStore } from '@/stores/appStore'
import Sidebar from './Sidebar'
import Navbar from './Navbar'
import TagsView from './TagsView'

export default function Layout() {
  const { sidebar, device, toggleDevice } = useAppStore()

  useEffect(() => {
    const handleResize = () => {
      const isMobile = window.innerWidth < 992
      toggleDevice(isMobile ? 'mobile' : 'desktop')
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [toggleDevice])

  const sidebarWidth = sidebar.opened ? 220 : 64

  return (
    <div className="h-full flex">
      <Sidebar />

      <div
        className="flex-1 flex flex-col layout-transition"
        style={{
          marginLeft: device === 'mobile' ? 0 : sidebarWidth,
        }}
      >
        <Navbar />
        <TagsView />

        <main className="flex-1 p-6 overflow-y-auto bg-content-bg">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
