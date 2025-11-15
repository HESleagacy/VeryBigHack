import React, { useEffect, useState, useRef } from 'react'

const API_URL = import.meta.env.VITE_REACT_APP_API_URL || 'http://localhost:3001/api/v1'

function Table({ title, data, columns }) {
  return (
    <div className="table">
      <h3>{title}</h3>
      <table>
        <thead>
          <tr>{columns.map(c => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i}>
              {columns.map(col => <td key={col}>{String(row[col] ?? '')}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Admin() {
  const [users, setUsers] = useState([])
  const [history, setHistory] = useState([])
  const [threats, setThreats] = useState([])
  const timer = useRef(null)

  async function fetchAll() {
    try {
      const [uRes, hRes, tRes] = await Promise.all([
        fetch(`${API_URL}/users`),
        fetch(`${API_URL}/system-history`),
        fetch(`${API_URL}/threat-log`)
      ])
      const [u, h, t] = await Promise.all([uRes.json(), hRes.json(), tRes.json()])
      setUsers(u)
      setHistory(h)
      setThreats(t)
    } catch (e) {
      console.error('Fetch failed', e)
    }
  }

  useEffect(() => {
    fetchAll()
    timer.current = setInterval(fetchAll, 3000)
    return () => clearInterval(timer.current)
  }, [])

  return (
    <div className="admin-page">
      <h2>Live Forensic Dashboard</h2>
      <div className="grids">
        <Table title="Users" data={users} columns={["userId","suspicion_score","is_human_verified","last_seen"]} />
        <Table title="Query Log (recent)" data={history} columns={["userId","prompt","response_type_served","timestamp"]} />
        <Table title="Threat Logs" data={threats} columns={["userId","attackType","blockchainTxHash","timestamp"]} />
      </div>
    </div>
  )
}
