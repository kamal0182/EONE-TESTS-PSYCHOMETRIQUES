import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import Button from '../../atoms/Button.jsx'
import Icon from '../../atoms/Icon.jsx'
import Input from '../../atoms/Input.jsx'
import AlertMessage from '../../molecules/AlertMessage.jsx'
import FormGroup from '../../molecules/FormGroup.jsx'
import MarketingHeaderFilters from '../../molecules/MarketingHeaderFilters.jsx'
import ConfirmDialog from '../../organisms/ConfirmDialog.jsx'
import DataTable from '../../organisms/DataTable.jsx'
import ProcessOverview from '../../organisms/ProcessOverview.jsx'
import { buildApiUrl } from '../../config/api.js'
import TestResultsDialog from './TestResultsDialog.jsx'

const HEADERS = [
  'Candidat',
  'Versions attribuées',
  'Statut',
  'Score global',
  'Action',
]

const EMPTY_CANDIDAT = { prenom: '', nom: '', email: '' }

function getErrorMessage(error, fallback) {
  const data = error?.response?.data
  const detail = data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  const firstKey = data && typeof data === 'object' ? Object.keys(data)[0] : null
  const firstValue = firstKey ? data[firstKey] : null
  if (Array.isArray(firstValue) && firstValue.length) return firstValue.join(' ')
  return fallback
}

function versionCode(version) {
  return String(version.version_name || '').replace(/^version\s*/i, 'V')
}

const STATUT_BADGES = {
  a_envoyer: { label: 'À envoyer', className: 'badge badge--pending' },
  envoye: { label: 'Envoyé', className: 'badge badge--warning' },
  en_cours: { label: 'En cours', className: 'badge badge--warning' },
  repondu: { label: 'Répondu', className: 'badge badge--success' },
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : ''
}

function formatScore(score) {
  if (score === null || score === undefined || score === '') return '-'
  const value = Number(score)
  return Number.isFinite(value) ? `${value.toLocaleString('fr-FR', { maximumFractionDigits: 2 })} %` : '-'
}

function GenerateTestModal({ isLoading, error, onClose, onSubmit }) {
  const [candidat, setCandidat] = useState(EMPTY_CANDIDAT)
  const [formError, setFormError] = useState('')

  function update(name, value) {
    setCandidat((current) => ({ ...current, [name]: value }))
  }

  function handleSubmit(event) {
    event.preventDefault()
    const payload = {
      prenom: candidat.prenom.trim(),
      nom: candidat.nom.trim(),
      email: candidat.email.trim(),
    }
    if (!payload.prenom || !payload.nom || !payload.email) {
      setFormError('Le prénom, le nom et l’email du candidat sont obligatoires.')
      return
    }
    setFormError('')
    onSubmit(payload)
  }

  return (
    <div className="modal-overlay" role="presentation" onClick={isLoading ? undefined : onClose}>
      <form
        className="modal qb-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="generate-test-title"
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <div className="modal__header">
          <h2 className="modal__title" id="generate-test-title">Générer un test</h2>
          <button type="button" className="icon-button" onClick={onClose} disabled={isLoading} aria-label="Fermer">
            <Icon name="close" />
          </button>
        </div>
        <div className="modal__body qb-modal__body">
          <p className="qb-modal__context">
            Une version est tirée au hasard pour chaque core value.
          </p>
          <FormGroup label="Prénom" required>
            <Input
              type="text"
              value={candidat.prenom}
              maxLength={150}
              onChange={(event) => update('prenom', event.target.value)}
              placeholder="Prénom du candidat"
              autoFocus
            />
          </FormGroup>
          <FormGroup label="Nom" required>
            <Input
              type="text"
              value={candidat.nom}
              maxLength={150}
              onChange={(event) => update('nom', event.target.value)}
              placeholder="Nom du candidat"
            />
          </FormGroup>
          <FormGroup label="Email" required>
            <Input
              type="email"
              value={candidat.email}
              onChange={(event) => update('email', event.target.value)}
              placeholder="email@exemple.com"
            />
          </FormGroup>
          {formError || error ? (
            <p className="status-comment-dialog__error">{formError || error}</p>
          ) : null}
        </div>
        <div className="modal__footer">
          <Button variant="secondary" onClick={onClose} disabled={isLoading}>Annuler</Button>
          <Button variant="primary" type="submit" disabled={isLoading}>
            {isLoading ? 'Génération…' : 'Générer le test'}
          </Button>
        </div>
      </form>
    </div>
  )
}

export default function TestsPsychometriquesPage({ user, roleTitle }) {
  const [tests, setTests] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [sendingId, setSendingId] = useState('')
  const [resultsTestId, setResultsTestId] = useState('')
  const [showGenerate, setShowGenerate] = useState(false)
  const [generateError, setGenerateError] = useState('')
  const [generating, setGenerating] = useState(false)
  const [toDelete, setToDelete] = useState(null)

  const authHeaders = useMemo(
    () => (user?.token ? { Authorization: `Bearer ${user.token}` } : {}),
    [user?.token],
  )

  useEffect(() => {
    let cancelled = false
    async function loadTests() {
      setLoading(true)
      setError('')
      try {
        const response = await axios.get(
          buildApiUrl('/api/tests-psychometriques/'),
          { headers: authHeaders },
        )
        if (!cancelled) setTests(Array.isArray(response.data) ? response.data : [])
      } catch (requestError) {
        if (!cancelled) {
          setTests([])
          setError(getErrorMessage(requestError, 'Impossible de charger les tests psychométriques.'))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadTests()
    return () => { cancelled = true }
  }, [authHeaders])

  const filteredTests = useMemo(() => {
    const term = searchTerm.trim().toLocaleLowerCase('fr')
    if (!term) return tests
    return tests.filter((test) => [
      test.nom,
      test.prenom,
      test.email,
    ].some((value) => String(value || '').toLocaleLowerCase('fr').includes(term)))
  }, [searchTerm, tests])

  function openGenerate() {
    setGenerateError('')
    setShowGenerate(true)
  }

  async function generateTest(payload) {
    setError('')
    setSuccess('')
    setGenerateError('')
    setGenerating(true)
    try {
      const response = await axios.post(
        buildApiUrl('/api/tests-psychometriques/'),
        payload,
        { headers: authHeaders },
      )
      setTests((previous) => [response.data, ...previous])
      setShowGenerate(false)
      setSuccess(`Test généré pour ${payload.prenom} ${payload.nom}. Cliquez sur « Copier le lien » pour le transmettre au candidat.`)
    } catch (requestError) {
      // La modale reste ouverte : l'admin corrige sans ressaisir.
      setGenerateError(getErrorMessage(requestError, 'Impossible de générer le test.'))
    } finally {
      setGenerating(false)
    }
  }

  async function copyLink(test, message = 'Lien du test copié dans le presse-papiers.') {
    setError('')
    try {
      await navigator.clipboard.writeText(test.lien)
      setSuccess(message)
    } catch {
      window.prompt('Copiez le lien du test :', test.lien)
    }
  }

  /**
   * « lien » : crée le lien (statut Envoyé) ; « prolonger » : +7 jours de validité.
   * Dans les deux cas le lien est copié pour être transmis au candidat.
   */
  async function linkAction(test, operation) {
    setSendingId(test.id)
    setError('')
    setSuccess('')
    try {
      const response = await axios.post(
        buildApiUrl(`/api/tests-psychometriques/${test.id}/${operation}/`),
        {},
        { headers: authHeaders },
      )
      const updated = response.data
      setTests((previous) => previous.map((item) => (item.id === test.id ? updated : item)))
      const validite = `valable jusqu’au ${formatDate(updated.token_expires_at)}`
      await copyLink(updated, operation === 'prolonger'
        ? `Lien prolongé (${validite}) et copié. Transmettez-le à ${test.email}.`
        : `Lien copié (${validite}). Transmettez-le à ${test.email}.`)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Impossible de créer le lien du test.'))
    } finally {
      setSendingId('')
    }
  }

  async function confirmDelete() {
    setSendingId(toDelete.id)
    setError('')
    setSuccess('')
    try {
      await axios.delete(
        buildApiUrl(`/api/tests-psychometriques/${toDelete.id}/`),
        { headers: authHeaders },
      )
      setTests((previous) => previous.filter((item) => item.id !== toDelete.id))
      setSuccess('Test supprimé.')
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Impossible de supprimer le test.'))
    } finally {
      setSendingId('')
      setToDelete(null)
    }
  }

  function renderStatut(test) {
    const badge = STATUT_BADGES[test.statut]
    if (!badge) return '-'
    let detail = ''
    if (test.statut === 'envoye') {
      detail = `Lien valable jusqu’au ${formatDate(test.token_expires_at)}`
    } else if (test.statut === 'repondu') {
      detail = formatDate(test.submitted_at)
    }
    return (
      <>
        <span className={badge.className}>{badge.label}</span>
        {detail ? <div className="test-list__statut-detail">{detail}</div> : null}
      </>
    )
  }

  function renderMainAction(test) {
    const busy = sendingId === test.id
    if (test.statut === 'a_envoyer') {
      return (
        <Button
          variant="primary"
          size="sm"
          className="test-list__action"
          icon={<Icon name="externalLink" size={14} />}
          disabled={busy}
          onClick={() => linkAction(test, 'lien')}
        >
          {busy ? 'Création…' : 'Copier le lien'}
        </Button>
      )
    }
    if (test.statut === 'envoye' || test.statut === 'en_cours') {
      return (
        <Button
          variant="primary"
          size="sm"
          className="test-list__action"
          icon={<Icon name="externalLink" size={14} />}
          onClick={() => copyLink(test)}
        >
          Copier le lien
        </Button>
      )
    }
    if (test.statut === 'repondu') {
      return (
        <Button
          variant="primary"
          size="sm"
          className="test-list__action"
          onClick={() => setResultsTestId(test.id)}
        >
          Voir les résultats
        </Button>
      )
    }
    return null
  }

  function renderAction(test) {
    const busy = sendingId === test.id
    return (
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {renderMainAction(test)}
        {test.statut === 'envoye' ? (
          <Button
            variant="secondary"
            size="sm"
            className="test-list__action"
            icon={<Icon name="refresh" size={14} />}
            disabled={busy}
            title="Prolonger la validité du lien de 7 jours"
            onClick={() => linkAction(test, 'prolonger')}
          >
            {busy ? 'Prolongation…' : 'Prolonger'}
          </Button>
        ) : null}
        <Button
          variant="ghost-danger"
          size="sm"
          className="test-list__action"
          disabled={sendingId === test.id}
          onClick={() => setToDelete(test)}
        >
          Supprimer
        </Button>
      </div>
    )
  }

  const rows = filteredTests.map((test) => ({
    key: test.id,
    cells: [
      {
        content: (
          <>
            <div><strong>{[test.prenom, test.nom].filter(Boolean).join(' ') || '-'}</strong></div>
            <div>{test.email || '-'}</div>
          </>
        ),
      },
      {
        content: test.versions?.length
          ? (
            <span
              className="versions-pill"
              title={test.versions.map((item) => `${item.core_value_name} : ${item.version_name}`).join('\n')}
            >
              {test.versions.map(versionCode).join(' · ')}
            </span>
          )
          : '-',
      },
      { content: renderStatut(test) },
      { content: formatScore(test.score_global) },
      { content: renderAction(test) },
    ],
  }))

  return (
    <ProcessOverview
      title="TESTS PSYCHOMÉTRIQUES"
      breadcrumb={`${roleTitle} > Tests psychométriques`}
      cardIcon={<Icon name="folder" size={18} />}
      cardTitle="Tests psychométriques"
      action={(
        <Button size="sm" variant="primary" icon={<Icon name="plus" size={14} />} onClick={openGenerate}>
          Générer un test
        </Button>
      )}
      beforeTable={(
        <MarketingHeaderFilters
          searchValue={searchTerm}
          onSearchChange={setSearchTerm}
          searchPlaceholder="Rechercher"
          showFilters={false}
        />
      )}
    >
      <AlertMessage message={error} />
      <AlertMessage message={success} type="success" />
      <DataTable
        headers={HEADERS}
        rows={rows}
        emptyState={{
          icon: '📄',
          title: loading ? 'Chargement...' : 'Aucun test',
          text: loading
            ? 'Chargement des tests psychométriques.'
            : 'Cliquez sur « Générer un test » pour créer le test d’un candidat.',
        }}
      />
      {showGenerate ? (
        <GenerateTestModal
          isLoading={generating}
          error={generateError}
          onClose={() => setShowGenerate(false)}
          onSubmit={generateTest}
        />
      ) : null}
      {resultsTestId ? (
        <TestResultsDialog
          testId={resultsTestId}
          authHeaders={authHeaders}
          onClose={() => setResultsTestId('')}
        />
      ) : null}
      {toDelete ? (
        <ConfirmDialog
          title="Supprimer le test"
          message={`Supprimer le test de ${toDelete.prenom} ${toDelete.nom} ? Ses réponses seront définitivement perdues et le lien ne fonctionnera plus.`}
          confirmLabel="Supprimer"
          isLoading={sendingId === toDelete.id}
          onCancel={() => setToDelete(null)}
          onConfirm={confirmDelete}
        />
      ) : null}
    </ProcessOverview>
  )
}
