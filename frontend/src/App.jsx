import { useEffect, useState } from 'react'
import axios from 'axios'
import { buildApiUrl } from './config/api.js'
import { loadSession, saveSession } from './utils/session.js'
import CandidatTestPage from './CandidatTestPage.jsx'
import LoginPage from './LoginPage.jsx'
import Dashboard from './Dashboard.jsx'

function AdminApp() {
  const [user, setUser] = useState(loadSession)

  useEffect(() => {
    const onLogout = () => {
      saveSession(null)
      setUser(null)
    }
    window.addEventListener('eone-logout', onLogout)
    return () => window.removeEventListener('eone-logout', onLogout)
  }, [])

  function handleLogin(session) {
    saveSession(session)
    setUser(session)
  }

  async function handleLogout() {
    try {
      await axios.post(buildApiUrl('/api/auth/logout/'), {}, {
        headers: { Authorization: `Bearer ${user.token}` },
      })
    } catch {
      // Le jeton est supprimé localement dans tous les cas.
    }
    saveSession(null)
    setUser(null)
  }

  if (!user) return <LoginPage onLogin={handleLogin} />
  return <Dashboard user={user} onLogout={handleLogout} />
}

export default function App() {
  // Lien public envoyé au candidat.
  if (window.location.pathname === '/passer-test') return <CandidatTestPage />
  return <AdminApp />
}
