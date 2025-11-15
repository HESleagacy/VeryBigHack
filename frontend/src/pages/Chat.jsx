import React, { useState } from 'react'

const API_URL = import.meta.env.VITE_REACT_APP_API_URL || 'http://localhost:3001/api/v1'

function ChatBox({ messages }) {
  return (
    <div className="chat-box">
      {messages.map((m, i) => (
        <div key={i} className={`msg ${m.user === 'User_Attacker' ? 'attacker' : 'user'}`}>
          <strong>{m.user}:</strong> {m.text}
        </div>
      ))}
    </div>
  )
}

export default function Chat() {
  const [user, setUser] = useState('User_A')
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)

  async function sendPrompt(p, u) {
    setLoading(true)
    setMessages(prev => [...prev, { user: u, text: p }])
    try {
      const res = await fetch(`${API_URL}/prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: u, prompt: p })
      })
      const data = await res.json()
      const text = data.response || data.noisy || JSON.stringify(data)
      setMessages(prev => [...prev, { user: 'system', text }])
    } catch (e) {
      setMessages(prev => [...prev, { user: 'system', text: 'Error: ' + e.message }])
    } finally {
      setLoading(false)
    }
  }

  function onSubmit(e) {
    e.preventDefault()
    if (!prompt) return
    sendPrompt(prompt, user)
    setPrompt('')
  }

  // Simple attacker spam: send 5 prompts quickly
  async function attackerSpam() {
    for (let i = 0; i < 5; i++) {
      await sendPrompt(`malicious prompt ${i + 1}`, 'User_Attacker')
    }
  }

  return (
    <div className="chat-page">
      <div className="controls">
        <label>
          Role:
          <select value={user} onChange={e => setUser(e.target.value)}>
            <option value="User_A">User_A (benign)</option>
            <option value="User_Attacker">User_Attacker (attacker)</option>
          </select>
        </label>
        <button onClick={attackerSpam} className="danger">Attacker: Spam 5x</button>
      </div>

      <ChatBox messages={messages} />

      <form onSubmit={onSubmit} className="prompt-form">
        <input value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Enter prompt..." />
        <button type="submit" disabled={loading}>{loading ? 'Waiting...' : 'Send'}</button>
      </form>
    </div>
  )
}
