import { Routes, Route } from 'react-router-dom'
import { DialogProvider } from '@/components/ReDialog'
import AuthGuard from '@/components/AuthGuard'
import ErrorBoundary from '@/components/ErrorBoundary'
import Layout from './layout'
import Dashboard from './views/Dashboard'
import Books from './views/Books'
import Chapters from './views/Chapters'
import Tags from './views/Tags'
import Users from './views/Users'
import Progress from './views/Progress'
import Stats from './views/Stats'
import Favorites from './views/Favorites'
import Crawler from './views/Crawler'
import Login from './views/Login'
import ErrorPage from './views/ErrorPage'

function App() {
  return (
    <DialogProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/error/403" element={<ErrorPage code={403} />} />
        <Route path="/error/404" element={<ErrorPage code={404} />} />
        <Route path="/error/500" element={<ErrorPage code={500} />} />
        <Route path="/" element={<AuthGuard><Layout /></AuthGuard>}>
          <Route index element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
          <Route path="dashboard" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
          <Route path="books" element={<ErrorBoundary><Books /></ErrorBoundary>} />
          <Route path="chapters" element={<ErrorBoundary><Chapters /></ErrorBoundary>} />
          <Route path="tags" element={<ErrorBoundary><Tags /></ErrorBoundary>} />
          <Route path="users" element={<ErrorBoundary><Users /></ErrorBoundary>} />
          <Route path="progress" element={<ErrorBoundary><Progress /></ErrorBoundary>} />
          <Route path="stats" element={<ErrorBoundary><Stats /></ErrorBoundary>} />
          <Route path="favorites" element={<ErrorBoundary><Favorites /></ErrorBoundary>} />
          <Route path="crawler" element={<ErrorBoundary><Crawler /></ErrorBoundary>} />
          <Route path="*" element={<ErrorPage code={404} />} />
        </Route>
      </Routes>
    </DialogProvider>
  )
}

export default App
