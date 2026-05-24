import { Suspense, lazy } from 'react'
import { Routes, Route } from 'react-router-dom'
import { DialogProvider } from '@/components/ReDialog'
import AuthGuard from '@/components/AuthGuard'
import ErrorBoundary from '@/components/ErrorBoundary'
import Layout from './layout'
import Login from './views/Login'
import ErrorPage from './views/ErrorPage'
import { Spinner } from '@/components/Loading'

const Discovery = lazy(() => import('./views/Discovery'))
const Chapters = lazy(() => import('./views/Chapters'))
const Dashboard = lazy(() => import('./views/Dashboard'))
const Books = lazy(() => import('./views/Books'))
const Tags = lazy(() => import('./views/Tags'))
const Users = lazy(() => import('./views/Users'))
const Progress = lazy(() => import('./views/Progress'))
const Stats = lazy(() => import('./views/Stats'))
const Favorites = lazy(() => import('./views/Favorites'))
const Crawler = lazy(() => import('./views/Crawler'))

function LazyPage({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<Spinner />}>
      {children}
    </Suspense>
  )
}

function App() {
  return (
    <DialogProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/error/403" element={<ErrorPage code={403} />} />
        <Route path="/error/404" element={<ErrorPage code={404} />} />
        <Route path="/error/500" element={<ErrorPage code={500} />} />

        <Route index element={<ErrorBoundary><LazyPage><Discovery /></LazyPage></ErrorBoundary>} />
        <Route path="discovery" element={<ErrorBoundary><LazyPage><Discovery /></LazyPage></ErrorBoundary>} />
        <Route path="books/:bookId" element={<ErrorBoundary><LazyPage><Chapters /></LazyPage></ErrorBoundary>} />

        <Route path="admin-dashboard" element={<AuthGuard adminOnly><Layout /></AuthGuard>}>
          <Route index element={<ErrorBoundary><LazyPage><Dashboard /></LazyPage></ErrorBoundary>} />
          <Route path="books" element={<ErrorBoundary><LazyPage><Books /></LazyPage></ErrorBoundary>} />
          <Route path="chapters" element={<ErrorBoundary><LazyPage><Chapters /></LazyPage></ErrorBoundary>} />
          <Route path="tags" element={<ErrorBoundary><LazyPage><Tags /></LazyPage></ErrorBoundary>} />
          <Route path="users" element={<ErrorBoundary><LazyPage><Users /></LazyPage></ErrorBoundary>} />
          <Route path="progress" element={<ErrorBoundary><LazyPage><Progress /></LazyPage></ErrorBoundary>} />
          <Route path="stats" element={<ErrorBoundary><LazyPage><Stats /></LazyPage></ErrorBoundary>} />
          <Route path="favorites" element={<ErrorBoundary><LazyPage><Favorites /></LazyPage></ErrorBoundary>} />
          <Route path="crawler" element={<ErrorBoundary><LazyPage><Crawler /></LazyPage></ErrorBoundary>} />
        </Route>

        <Route path="*" element={<ErrorPage code={404} />} />
      </Routes>
    </DialogProvider>
  )
}

export default App
