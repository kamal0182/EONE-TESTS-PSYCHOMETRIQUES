import { useState } from 'react'
import axios from 'axios'
import { buildApiUrl } from './config/api.js'
import Button from './atoms/Button.jsx'
import Icon from './atoms/Icon.jsx'
import AlertMessage from './molecules/AlertMessage.jsx'
import InputField from './molecules/InputField.jsx'
import AuthLayout from './templates/AuthLayout.jsx'

function getErrorMessage(error) {
  if (!error?.response) return "Service d'authentification indisponible."
  const data = error.response.data
  if (typeof data?.detail === 'string') return data.detail
  return 'Identifiant ou mot de passe incorrect.'
}

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  async function handleLogin() {
    setError('')
    if (!username.trim()) {
      setError('Veuillez saisir votre identifiant.')
      return
    }
    if (!password) {
      setError('Veuillez saisir votre mot de passe.')
      return
    }
    setLoading(true)
    try {
      const { data } = await axios.post(buildApiUrl('/api/auth/login/'), {
        username: username.trim(),
        password,
      })
      onLogin({ token: data.token, username: data.username, nom: data.nom })
    } catch (requestError) {
      setError(getErrorMessage(requestError))
      setLoading(false)
    }
  }

  function onKeyDown(event) {
    if (event.key === 'Enter') handleLogin()
  }

  return (
    <AuthLayout>
      <div className="login-card">
        <div className="login-card-header">
          <div className="brand-logo">
            <img src="/image_enosisapp.png?v=eone-20260611-new" alt="enosisapp Group Logo" />
          </div>
          <div className="login-brand-name">eOne</div>
          <h1 className="login-title">
            Bienvenue sur <span className="login-title-brand">eOne</span>
          </h1>
          <p className="login-subtitle">Tests psychométriques — espace administrateur</p>
        </div>

        <AlertMessage message={error} />

        <InputField
          label="Identifiant"
          leftIcon={<Icon name="mail" size={15} />}
          inputProps={{
            type: 'text',
            value: username,
            onChange: (event) => setUsername(event.target.value),
            placeholder: 'admin',
            autoComplete: 'username',
            autoFocus: true,
            onKeyDown,
          }}
        />

        <InputField
          label="Mot de passe"
          leftIcon={<Icon name="lock" size={15} />}
          rightSlot={(
            <button
              type="button"
              className="icon-button"
              onClick={() => setShowPassword((value) => !value)}
              aria-label="Afficher ou masquer le mot de passe"
            >
              <Icon name={showPassword ? 'eye' : 'eyeOff'} />
            </button>
          )}
          inputProps={{
            type: showPassword ? 'text' : 'password',
            value: password,
            onChange: (event) => setPassword(event.target.value),
            placeholder: '********',
            autoComplete: 'current-password',
            onKeyDown,
          }}
        />

        <Button variant="login" onClick={handleLogin} disabled={loading}>
          {loading ? 'Connexion...' : 'Se connecter'}
        </Button>

        <p className="support-text">
          Besoin d&apos;aide ? <a href="mailto:eone.support@enosis.ma">Contacter le support</a>
        </p>
      </div>
    </AuthLayout>
  )
}
