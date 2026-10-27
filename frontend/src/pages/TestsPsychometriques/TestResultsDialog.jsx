import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import Button from '../../atoms/Button.jsx'
import Icon from '../../atoms/Icon.jsx'
import AlertMessage from '../../molecules/AlertMessage.jsx'
import { buildApiUrl } from '../../config/api.js'

const TABS = [
  { id: 'radar', label: 'Vue radar' },
  { id: 'details', label: 'Détail des réponses' },
]

// Niveaux d'alignement affichés sous le score global.
const LEVELS = [
  { min: 85, label: 'Très bon alignement' },
  { min: 70, label: 'Bon alignement' },
  { min: 50, label: 'Alignement moyen' },
  { min: 0, label: 'Alignement faible' },
]

function toNumber(value) {
  const number = Number(value)
  return value === null || value === undefined || value === '' || !Number.isFinite(number) ? null : number
}

function formatPercent(value, digits = 0) {
  const number = toNumber(value)
  return number === null ? '-' : `${number.toLocaleString('fr-FR', { maximumFractionDigits: digits })}%`
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '-'
}

function formatDuration(start, end) {
  if (!start || !end) return '-'
  const seconds = Math.max(0, Math.round((new Date(end) - new Date(start)) / 1000))
  return `${Math.floor(seconds / 60)} min ${String(seconds % 60).padStart(2, '0')} s`
}

function levelFor(score) {
  const number = toNumber(score)
  return number === null ? null : LEVELS.find((level) => number >= level.min)
}

function splitLabel(label) {
  const words = String(label).split(' ')
  if (words.length < 3) return [label]
  const middle = Math.ceil(words.length / 2)
  return [words.slice(0, middle).join(' '), words.slice(middle).join(' ')]
}

const RADAR = { width: 520, height: 400, cx: 260, cy: 205, radius: 140 }

function RadarChart({ dimensions }) {
  const [hovered, setHovered] = useState(null)
  const count = dimensions.length
  if (count < 3) {
    return <p className="test-view__empty">Au moins trois core values sont nécessaires pour la vue radar.</p>
  }
  const angle = (index) => (-Math.PI / 2) + (index * 2 * Math.PI) / count
  const point = (index, ratio) => ({
    x: RADAR.cx + Math.cos(angle(index)) * RADAR.radius * ratio,
    y: RADAR.cy + Math.sin(angle(index)) * RADAR.radius * ratio,
  })
  const ring = (ratio) => dimensions.map((_, index) => {
    const p = point(index, ratio)
    return `${p.x},${p.y}`
  }).join(' ')
  const values = dimensions.map((item, index) => ({
    ...item,
    ...point(index, Math.min(100, Math.max(0, item.value ?? 0)) / 100),
  }))
  const active = hovered === null ? null : values[hovered]

  return (
    <div className="test-results__radar">
      <svg
        viewBox={`0 0 ${RADAR.width} ${RADAR.height}`}
        role="img"
        aria-label={`Radar des scores : ${dimensions.map((item) => `${item.name} ${formatPercent(item.value)}`).join(', ')}`}
      >
        {[0.2, 0.4, 0.6, 0.8, 1].map((ratio) => (
          <polygon key={ratio} points={ring(ratio)} className="test-results__radar-grid" />
        ))}
        {dimensions.map((item, index) => {
          const end = point(index, 1)
          return <line key={item.id} x1={RADAR.cx} y1={RADAR.cy} x2={end.x} y2={end.y} className="test-results__radar-axis" />
        })}
        {[20, 40, 60, 80, 100].map((tick) => (
          <text key={tick} x={RADAR.cx - 7} y={RADAR.cy - (RADAR.radius * tick) / 100 + 3} textAnchor="end" className="test-results__radar-tick">
            {tick}
          </text>
        ))}
        <polygon points={values.map((item) => `${item.x},${item.y}`).join(' ')} className="test-results__radar-area" />
        {dimensions.map((item, index) => {
          const labelPoint = point(index, 1.16)
          const cos = Math.cos(angle(index))
          const anchor = Math.abs(cos) < 0.2 ? 'middle' : cos > 0 ? 'start' : 'end'
          const lines = splitLabel(item.name)
          const offset = Math.sin(angle(index)) < -0.5 ? -(lines.length - 1) * 14 : 0
          return (
            <text key={item.id} x={labelPoint.x} y={labelPoint.y + 4 + offset} textAnchor={anchor} className="test-results__radar-label">
              {lines.map((line, lineIndex) => (
                <tspan key={line} x={labelPoint.x} dy={lineIndex ? 14 : 0}>{line}</tspan>
              ))}
            </text>
          )
        })}
        {values.map((item, index) => (
          <g
            key={item.id}
            onMouseEnter={() => setHovered(index)}
            onMouseLeave={() => setHovered(null)}
            onFocus={() => setHovered(index)}
            onBlur={() => setHovered(null)}
            tabIndex={0}
            aria-label={`${item.name} : ${formatPercent(item.value)}`}
          >
            <circle cx={item.x} cy={item.y} r={14} className="test-results__radar-hit" />
            <circle cx={item.x} cy={item.y} r={hovered === index ? 6 : 5} className="test-results__radar-point" />
          </g>
        ))}
      </svg>
      {active ? (
        <div
          className="test-results__tooltip"
          style={{ left: `${(active.x / RADAR.width) * 100}%`, top: `${(active.y / RADAR.height) * 100}%` }}
        >
          <span className="test-results__tooltip-name">{active.name}</span>
          <span className="test-results__tooltip-value">{formatPercent(active.value, 2)}</span>
          <span className="test-results__tooltip-meta">{active.answered}/{active.total} réponses</span>
        </div>
      ) : null}
    </div>
  )
}

export default function TestResultsDialog({ testId, authHeaders, onClose }) {
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('radar')

  useEffect(() => {
    let cancelled = false
    axios.get(
      buildApiUrl(`/api/tests-psychometriques/${testId}/`),
      { headers: authHeaders },
    )
      .then((response) => { if (!cancelled) setResult(response.data) })
      .catch((requestError) => {
        if (cancelled) return
        const detail = requestError?.response?.data?.detail
        setError(typeof detail === 'string' && detail ? detail : 'Impossible de charger les résultats.')
      })
    return () => { cancelled = true }
  }, [authHeaders, testId])

  const dimensions = useMemo(() => (result?.sections || []).map((section) => ({
    id: section.test_version_id,
    name: section.core_value_name,
    version: String(section.version_name || '').replace(/^version\s*/i, 'V'),
    value: toNumber(section.percentage),
    total: section.questions.length,
    answered: section.questions.filter((question) => question.selected_answer_id).length,
  })), [result])

  const candidat = result ? [result.prenom, result.nom].filter(Boolean).join(' ') || result.email : ''
  const score = toNumber(result?.score_global)
  const level = levelFor(score)
  const totalQuestions = dimensions.reduce((sum, item) => sum + item.total, 0)
  const totalAnswered = dimensions.reduce((sum, item) => sum + item.answered, 0)

  return (
    <div className="modal-overlay">
      <div className="modal test-results">
        <div className="modal__header">
          <h2 className="modal__title">Résultats du test{candidat ? ` · ${candidat}` : ''}</h2>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Fermer">
            <Icon name="close" />
          </button>
        </div>

        <div className="modal__body">
          <AlertMessage message={error} />
          {!result && !error ? <p className="test-view__empty">Chargement des résultats…</p> : null}
          {result ? (
            <>
              <div className="test-results__top">
                <div className="test-results__hero">
                  <span className="test-results__hero-label">Score global pondéré</span>
                  <span className="test-results__hero-value">{formatPercent(score)}</span>
                  <span className="test-results__hero-level">{level?.label || 'Non disponible'}</span>
                  <div className="test-results__hero-track">
                    <div className="test-results__hero-bar" style={{ width: `${Math.min(100, score ?? 0)}%` }} />
                  </div>
                </div>
                <div className="test-results__synthese">
                  <dl className="test-results__meta">
                    <div><dt>Email</dt><dd>{result.email || '-'}</dd></div>
                    <div><dt>Terminé le</dt><dd>{formatDate(result.submitted_at)}</dd></div>
                    <div><dt>Durée</dt><dd>{formatDuration(result.started_at, result.submitted_at)}</dd></div>
                    <div><dt>Réponses</dt><dd>{totalAnswered}/{totalQuestions}</dd></div>
                  </dl>
                </div>
              </div>

              <div className="test-results__tabs" role="tablist">
                {TABS.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    role="tab"
                    aria-selected={tab === item.id}
                    className={`test-results__tab${tab === item.id ? ' test-results__tab--active' : ''}`}
                    onClick={() => setTab(item.id)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              {tab === 'radar' ? (
                <div className="test-results__radar-layout">
                  <RadarChart dimensions={dimensions} />
                  <ul className="test-results__cards">
                    {dimensions.map((item) => (
                      <li key={item.id} className="test-results__card">
                        <div className="test-results__card-head">
                          <span className="test-results__card-name">{item.name}</span>
                          <span className="test-results__card-value">{formatPercent(item.value)}</span>
                        </div>
                        <div className="test-results__card-track">
                          <div className="test-results__card-bar" style={{ width: `${Math.min(100, item.value ?? 0)}%` }} />
                        </div>
                        <span className="test-results__card-meta">
                          Version {item.version || '-'} · {item.answered}/{item.total} réponses
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="test-results__details">
                  {result.sections.map((section) => (
                    <section key={section.test_version_id} className="test-results__section">
                      <header className="test-results__section-head">
                        <span className="test-results__section-name">{section.core_value_name}</span>
                        <span className="test-results__card-value">{formatPercent(section.percentage)}</span>
                      </header>
                      <ol className="test-results__questions">
                        {section.questions.map((question, index) => {
                          const chosen = question.answers.find((answer) => answer.id === question.selected_answer_id)
                          return (
                            <li key={question.id} className="test-results__question">
                              <span className="test-results__question-index">{index + 1}</span>
                              <div className="test-results__question-body">
                                <div className="test-results__question-text">{question.text}</div>
                                {chosen ? (
                                  <div className="test-results__answer">
                                    <span className="test-results__answer-text">{chosen.text}</span>
                                    <span className="test-results__answer-score">{formatPercent(chosen.percentage)}</span>
                                  </div>
                                ) : (
                                  <div className="test-results__answer test-results__answer--missing">Sans réponse</div>
                                )}
                              </div>
                            </li>
                          )
                        })}
                      </ol>
                    </section>
                  ))}
                </div>
              )}
            </>
          ) : null}
        </div>

        <div className="modal__footer">
          <Button variant="secondary" onClick={onClose}>Fermer</Button>
        </div>
      </div>
    </div>
  )
}
