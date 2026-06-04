import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { useAppStore } from '@/stores/appStore'
import Sidebar from './Sidebar'
import Navbar from './Navbar'
import TagsView from './TagsView'

export default function Layout() {
  const { sidebar, device, closeSidebar, toggleDevice } = useAppStore()

  useEffect(() => {
    const handleResize = () => {
      const isMobile = window.innerWidth < 992
      toggleDevice(isMobile ? 'mobile' : 'desktop')
      if (isMobile && sidebar.opened) {
        closeSidebar()
      }
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [toggleDevice, closeSidebar, sidebar.opened])

  const sidebarWidth = sidebar.opened ? 220 : 64

  return (
    <div className="h-full flex">
      {/* 移动端侧边栏遮罩 */}
      {device === 'mobile' && sidebar.opened && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={closeSidebar}
        />
      )}
      {/* 移动端侧边栏 fixed 定位 */}
      <div className={device === 'mobile' ? 'fixed inset-y-0 left-0 z-50' : ''}>
        <Sidebar />
      </div>

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
