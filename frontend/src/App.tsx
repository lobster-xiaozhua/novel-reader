import { Routes, Route } from 'react-router-dom'
import { DialogProvider } from '@/components/ReDialog'
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
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="books" element={<Books />} />
          <Route path="chapters" element={<Chapters />} />
          <Route path="tags" element={<Tags />} />
          <Route path="users" element={<Users />} />
          <Route path="progress" element={<Progress />} />
          <Route path="stats" element={<Stats />} />
          <Route path="favorites" element={<Favorites />} />
          <Route path="crawler" element={<Crawler />} />
          <Route path="*" element={<ErrorPage code={404} />} />
        </Route>
      </Routes>
    </DialogProvider>
  )
}

export default App
