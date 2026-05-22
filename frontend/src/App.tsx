import { Routes, Route } from 'react-router-dom'
import Layout from './layout'
import Dashboard from './views/Dashboard'
import Books from './views/Books'
import Crawler from './views/Crawler'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="books" element={<Books />} />
        <Route path="crawler" element={<Crawler />} />
        <Route path="*" element={<Dashboard />} />
      </Route>
    </Routes>
  )
}

export default App
