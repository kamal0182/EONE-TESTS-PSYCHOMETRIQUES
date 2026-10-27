import { useCallback, useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { buildApiUrl } from './config/api.js'
import AuthLayout from './templates/AuthLayout.jsx'
import AlertMessage from './molecules/AlertMessage.jsx'
import Button from './atoms/Button.jsx'

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail
  return typeof detail === 'string' && detail.trim() ? detail : fallback
}

function formatRemaining(seconds) {
  const safe = Math.max(0, seconds)
  const minutes = String(Math.floor(safe / 60)).padStart(2, '0')
  return `${minutes}:${String(safe % 60).padStart(2, '0')}`
}

function MessageCard({ title, text, children }) {
  return (
    <AuthLayout>
      <div className="login-card">
        <div className="login-card-header">
          <div className="brand-logo">
            <img src="/image_enosisapp.png?v=eone-20260611-new" alt="enosisapp Group Logo" />
          </div>
          <div className="login-brand-name">eOne</div>
          <h1 className="login-title">{title}</h1>
          <p className="login-subtitle">{text}</p>
        </div>
        {children}
      </div>
    </AuthLayout>
  )
}

export default function CandidatTestPage() {
  const token = new URLSearchParams(window.location.search).get('token') || ''
  const apiBase = `/api/test-candidat/${encodeURIComponent(token)}`
  const [state, setState] = useState(null)
  const [fatalError, setFatalError] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [remaining, setRemaining] = useState(0)
  const [timedOut, setTimedOut] = useState(false)
  const deadlineRef = useRef(0)

  // Le serveur n'envoie que la question en cours (`state.question`) et sa
  // position (`state.question_index`) : la progression est imposée côté serveur.
  const applyState = useCallback((data) => {
    if (data?.statut === 'en_cours') {
      deadlineRef.current = Date.now() + (data.remaining_seconds || 0) * 1000
      setRemaining(data.remaining_seconds || 0)
    }
    setState(data)
  }, [])

  useEffect(() => {
    if (!token) return
    axios.get(buildApiUrl(`${apiBase}/`))
      .then((response) => applyState(response.data))
      .catch((requestError) => setFatalError(getErrorMessage(requestError, 'Ce lien de test est invalide.')))
  }, [apiBase, applyState, token])

  /**
   * Réponse refusée : on relit l'état réel sur le serveur. Si le test est
   * terminé entre-temps, c'est que le temps est écoulé.
   */
  const recoverFromError = useCallback(async (requestError, fallback) => {
    if (requestError?.response?.status === 429) {
      setError(getErrorMessage(requestError, fallback))
      return
    }
    try {
      const response = await axios.get(buildApiUrl(`${apiBase}/`))
      if (response.data?.statut === 'repondu') setTimedOut(true)
      applyState(response.data)
      if (response.data?.statut === 'en_cours') setError(getErrorMessage(requestError, fallback))
    } catch {
      setError(getErrorMessage(requestError, fallback))
    }
  }, [apiBase, applyState])

  const finish = useCallback(async (byTimeout = false) => {
    setBusy(true)
    try {
      const response = await axios.post(buildApiUrl(`${apiBase}/terminer/`))
      setTimedOut(byTimeout)
      setState(response.data)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Impossible de terminer le test.'))
    } finally {
      setBusy(false)
    }
  }, [apiBase])

  const running = state?.statut === 'en_cours'
  useEffect(() => {
    if (!running) return undefined
    const timer = window.setInterval(() => {
      const seconds = Math.round((deadlineRef.current - Date.now()) / 1000)
      setRemaining(seconds)
      if (seconds <= 0) {
        window.clearInterval(timer)
        finish(true)
      }
    }, 1000)
    return () => window.clearInterval(timer)
  }, [finish, running])

  const current = state?.question || null
  const currentIndex = state?.question_index || 0
  const totalQuestions = state?.nb_questions || 0
  const isLast = currentIndex === totalQuestions - 1

  async function start() {
    setBusy(true)
    setError('')
    try {
      const response = await axios.post(buildApiUrl(`${apiBase}/demarrer/`))
      applyState(response.data)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Impossible de démarrer le test.'))
    } finally {
      setBusy(false)
    }
  }

  async function handleAnswer(question, answer) {
    if (question.selected_answer_id === answer.id) return
    setBusy(true)
    setError('')
    try {
      const response = await axios.post(buildApiUrl(`${apiBase}/repondre/`), { answer_id: answer.id })
      applyState(response.data)
    } catch (requestError) {
      await recoverFromError(requestError, 'Impossible d’enregistrer la réponse.')
    } finally {
      setBusy(false)
    }
  }

  // Valide définitivement la question en cours ; le serveur renvoie la suivante
  // (ou le test terminé après la dernière).
  async function goNext() {
    setBusy(true)
    setError('')
    try {
      const response = await axios.post(buildApiUrl(`${apiBase}/suivant/`))
      applyState(response.data)
    } catch (requestError) {
      await recoverFromError(requestError, 'Impossible de passer à la question suivante.')
    } finally {
      setBusy(false)
    }
  }

  if (!token || fatalError) {
    return <MessageCard title="Lien indisponible" text={fatalError || 'Ce lien de test est invalide.'} />
  }

  if (!state) {
    return <MessageCard title="Chargement…" text="Préparation de votre test." />
  }

  if (state.statut === 'repondu') {
    return (
      <MessageCard
        title={timedOut ? 'Temps écoulé' : 'Merci !'}
        text={timedOut
          ? 'Le temps imparti est écoulé. Vos réponses ont été enregistrées.'
          : 'Votre test est terminé et vos réponses ont été enregistrées. Vous pouvez fermer cette page.'}
      />
    )
  }

  if (state.statut === 'envoye') {
    return (
      <MessageCard
        title={`Bonjour ${state.prenom || ''}`.trim()}
        text="Vous êtes invité(e) à passer un test psychométrique."
      >
        <AlertMessage message={error} />
        <ul className="candidat-test__rules">
          <li><strong>{state.nb_questions}</strong> questions, une seule réponse par question.</li>
          <li>Durée : <strong>{state.duree_minutes} minutes</strong>, le chrono démarre dès que vous cliquez sur « Commencer ».</li>
          <li>Une question validée ne peut plus être modifiée : il n’y a pas de retour en arrière.</li>
          <li>À la fin du temps, le test est clôturé automatiquement.</li>
        </ul>
        <Button variant="login" onClick={start} disabled={busy}>
          {busy ? 'Démarrage…' : 'Commencer le test'}
        </Button>
      </MessageCard>
    )
  }

  const progress = totalQuestions ? ((currentIndex + 1) / totalQuestions) * 100 : 0

  return (
    <div className="candidat-test">
      <div className="test-run">
        <div className="candidat-test__header">
          <div className="test-run__progress">
            <div className="test-run__progress-label">Progression globale</div>
            <div className="test-run__progress-count">
              Question {currentIndex + 1} sur {totalQuestions}
            </div>
            <div className="test-run__progress-track">
              <div className="test-run__progress-bar" style={{ width: `${progress}%` }} />
            </div>
          </div>
          <div className={`candidat-test__timer${remaining <= 120 ? ' candidat-test__timer--urgent' : ''}`}>
            <span className="candidat-test__timer-label">Temps restant</span>
            <span className="candidat-test__timer-value">{formatRemaining(remaining)}</span>
          </div>
        </div>

        <AlertMessage message={error} />

        <section className="test-run__card">
          {current ? (
            <>
              <header className="test-run__card-header">
                <span className="test-run__card-dimension">{current.core_value_name}</span>
                <span className="test-run__card-position">
                  Question {current.index_in_section + 1}/{current.section_size}
                </span>
              </header>
              <div className="test-run__card-body">
                <h2 className="test-run__question">{current.text}</h2>
                <p className="test-run__hint">Sélectionnez une seule réponse :</p>
                <div className="test-run__answers" role="radiogroup">
                  {current.answers.map((answer, answerIndex) => {
                    const selected = current.selected_answer_id === answer.id
                    return (
                      <button
                        key={answer.id}
                        type="button"
                        role="radio"
                        aria-checked={selected}
                        className={`test-run__answer${selected ? ' test-run__answer--selected' : ''}`}
                        disabled={busy}
                        onClick={() => handleAnswer(current, answer)}
                      >
                        <span className="test-run__answer-letter">
                          {String.fromCharCode(65 + answerIndex)}
                        </span>
                        <span className="test-run__answer-text">{answer.text}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            </>
          ) : null}
          <footer className="test-run__card-footer">
            <span className="test-run__autosave">
              {busy ? 'Enregistrement…' : '✓ Sauvegarde automatique'}
            </span>
            <div className="test-run__nav">
              <button
                type="button"
                className="test-run__nav-btn test-run__nav-btn--primary"
                disabled={busy || !current?.selected_answer_id}
                onClick={goNext}
              >
                {isLast ? 'Terminer ✓' : 'Suivant →'}
              </button>
            </div>
          </footer>
        </section>
      </div>
    </div>
  )
}
