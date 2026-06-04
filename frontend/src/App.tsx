import { Suspense, lazy } from 'react'
import { Routes, Route } from 'react-router-dom'
import { DialogProvider } from '@/components/ReDialog'
import AuthGuard from '@/components/AuthGuard'
import ErrorBoundary from '@/components/ErrorBoundary'
import Layout from './layout'
import Login from './views/Login'
import ErrorPage from './views/ErrorPage'
import { Spinner } from '@/components/Loading'

const Dashboard = lazy(() => import('./views/Dashboard'))
const HomePortal = lazy(() => import('./views/HomePortal'))
const Books = lazy(() => import('./views/Books'))
const BookDetail = lazy(() => import('./views/BookDetail'))
const Chapters = lazy(() => import('./views/Chapters'))
const Tags = lazy(() => import('./views/Tags'))
const Users = lazy(() => import('./views/Users'))
const Progress = lazy(() => import('./views/Progress'))
const Stats = lazy(() => import('./views/Stats'))
const Favorites = lazy(() => import('./views/Favorites'))
const Crawler = lazy(() => import('./views/Crawler'))
const Rankings = lazy(() => import('./views/Rankings'))
const SearchPage = lazy(() => import('./views/Search'))
const BookDirs = lazy(() => import('./views/BookDirs'))

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
        <Route path="/" element={<AuthGuard><Layout /></AuthGuard>}>
          <Route index element={<ErrorBoundary><LazyPage><HomePortal /></LazyPage></ErrorBoundary>} />
          <Route path="dashboard" element={<ErrorBoundary><LazyPage><Dashboard /></LazyPage></ErrorBoundary>} />
          <Route path="books" element={<ErrorBoundary><LazyPage><Books /></LazyPage></ErrorBoundary>} />
          <Route path="books/:id" element={<ErrorBoundary><LazyPage><BookDetail /></LazyPage></ErrorBoundary>} />
          <Route path="chapters" element={<ErrorBoundary><LazyPage><Chapters /></LazyPage></ErrorBoundary>} />
          <Route path="tags" element={<ErrorBoundary><LazyPage><Tags /></LazyPage></ErrorBoundary>} />
          <Route path="users" element={<ErrorBoundary><LazyPage><Users /></LazyPage></ErrorBoundary>} />
          <Route path="progress" element={<ErrorBoundary><LazyPage><Progress /></LazyPage></ErrorBoundary>} />
          <Route path="stats" element={<ErrorBoundary><LazyPage><Stats /></LazyPage></ErrorBoundary>} />
          <Route path="favorites" element={<ErrorBoundary><LazyPage><Favorites /></LazyPage></ErrorBoundary>} />
          <Route path="crawler" element={<ErrorBoundary><LazyPage><Crawler /></LazyPage></ErrorBoundary>} />
          <Route path="rankings" element={<ErrorBoundary><LazyPage><Rankings /></LazyPage></ErrorBoundary>} />
          <Route path="search" element={<ErrorBoundary><LazyPage><SearchPage /></LazyPage></ErrorBoundary>} />
          <Route path="book-dirs" element={<ErrorBoundary><LazyPage><BookDirs /></LazyPage></ErrorBoundary>} />
          <Route path="*" element={<ErrorPage code={404} />} />
        </Route>
      </Routes>
    </DialogProvider>
  )
}

export default App
