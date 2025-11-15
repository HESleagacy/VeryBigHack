import React from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import Chat from './pages/Chat'
import Admin from './pages/Admin'

export default function App() {
  return (
    <div className="app">
      <header>
        <h1>Sentinel Demo</h1>
        <nav>
          <Link to="/">Chat</Link>
          <Link to="/admin">Admin Dashboard</Link>
        </nav>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/admin" element={<Admin />} />
        </Routes>
      </main>
    </div>
  )
}
