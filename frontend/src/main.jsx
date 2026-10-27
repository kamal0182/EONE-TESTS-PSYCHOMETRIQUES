import React from 'react'
import ReactDOM from 'react-dom/client'
import axios from 'axios'
import App from './App.jsx'
import './styles.css'
import { injectThemeVars } from './tokens/theme.js'

// Jeton admin expiré ou supprimé : retour à l'écran de connexion.
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401 && error.config?.headers?.Authorization) {
      window.dispatchEvent(new Event('eone-logout'))
    }
    return Promise.reject(error)
  },
)

injectThemeVars()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
