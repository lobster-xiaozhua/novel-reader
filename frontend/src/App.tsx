import { Routes, Route } from 'react-router-dom'
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

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
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
        <Route path="*" element={<Dashboard />} />
      </Route>
    </Routes>
  )
}

export default App
