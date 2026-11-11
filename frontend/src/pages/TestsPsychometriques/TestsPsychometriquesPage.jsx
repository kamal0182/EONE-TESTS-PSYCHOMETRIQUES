import { useEffect, useMemo, useRef, useState } from 'react'
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

// Envoi groupé : la sélection part par lots (une requête et une connexion SMTP
// par lot) pour rester loin du délai maximal d'une requête.
const EMAIL_BATCH_SIZE = 20

// Seuls les tests non commencés peuvent recevoir le lien par email.
function canReceiveEmail(test) {
  return test.statut === 'a_envoyer' || test.statut === 'envoye'
}

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
  const [importing, setImporting] = useState(false)
  const [exporting, setExporting] = useState(false)
  // Détail des lignes ignorées (import) ou des emails non envoyés (envoi groupé).
  const [report, setReport] = useState(null)
  const fileInputRef = useRef(null)
  const [selectedIds, setSelectedIds] = useState(() => new Set())
  const [confirmBulk, setConfirmBulk] = useState(false)
  const [bulkProgress, setBulkProgress] = useState(null)

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

  // Sélection effective : un test qui a commencé entre-temps n'est plus envoyable.
  const selectedTests = useMemo(
    () => tests.filter((test) => selectedIds.has(test.id) && canReceiveEmail(test)),
    [selectedIds, tests],
  )
  const selectableVisible = useMemo(() => filteredTests.filter(canReceiveEmail), [filteredTests])
  const allVisibleSelected = selectableVisible.length > 0
    && selectableVisible.every((test) => selectedIds.has(test.id))
  const bulkSending = bulkProgress !== null

  function toggleSelected(testId) {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (next.has(testId)) next.delete(testId)
      else next.add(testId)
      return next
    })
  }

  // Sélectionne (ou désélectionne) tous les tests envoyables affichés, recherche comprise.
  function toggleAllVisible() {
    setSelectedIds((current) => {
      const next = new Set(current)
      selectableVisible.forEach((test) => {
        if (allVisibleSelected) next.delete(test.id)
        else next.add(test.id)
      })
      return next
    })
  }

  /**
   * Envoi groupé : génère le lien (si besoin) et l'envoie par email à chaque
   * candidat sélectionné. Les lots partent l'un après l'autre ; le tableau et
   * la progression sont mis à jour après chaque lot.
   */
  async function sendBulkEmails() {
    const targets = selectedTests
    setConfirmBulk(false)
    setError('')
    setSuccess('')
    setReport(null)
    setBulkProgress({ done: 0, total: targets.length })
    let sentCount = 0
    const rejected = []
    let stopError = ''
    for (let start = 0; start < targets.length; start += EMAIL_BATCH_SIZE) {
      const batch = targets.slice(start, start + EMAIL_BATCH_SIZE)
      try {
        const response = await axios.post(
          buildApiUrl('/api/tests-psychometriques/envoyer-emails/'),
          { ids: batch.map((test) => test.id) },
          { headers: authHeaders },
        )
        const sent = response.data?.sent || []
        const updated = new Map(sent.map((test) => [test.id, test]))
        setTests((previous) => previous.map((test) => updated.get(test.id) || test))
        setSelectedIds((current) => {
          const next = new Set(current)
          sent.forEach((test) => next.delete(test.id))
          return next
        })
        sentCount += sent.length
        rejected.push(...(response.data?.rejected || []))
      } catch (requestError) {
        // Erreur globale (SMTP injoignable, session expirée…) : inutile de continuer.
        stopError = getErrorMessage(requestError, 'Impossible d’envoyer les emails.')
        break
      }
      setBulkProgress({ done: Math.min(start + batch.length, targets.length), total: targets.length })
    }
    setBulkProgress(null)

    if (rejected.length) {
      setReport({
        title: 'Emails non envoyés',
        lines: rejected.map((item) => `${item.email || item.id} : ${item.message}`),
      })
    }
    if (sentCount) {
      setSuccess(`${sentCount} email(s) envoyé(s) avec le lien du test.`)
    }
    if (stopError) {
      setError(`${stopError} Envoi interrompu : ${targets.length - sentCount - rejected.length} candidat(s) non traité(s), toujours sélectionné(s).`)
    } else if (!sentCount) {
      setError('Aucun email envoyé.')
    }
  }

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

  /**
   * Import d'un fichier Excel/CSV (colonnes Prénom, Nom, Email) : le serveur
   * génère un test par candidat et renvoie les lignes ignorées avec la raison.
   */
  async function importFile(event) {
    const file = event.target.files?.[0]
    // Permet de réimporter le même fichier après correction.
    event.target.value = ''
    if (!file) return
    setError('')
    setSuccess('')
    setReport(null)
    setImporting(true)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const response = await axios.post(
        buildApiUrl('/api/tests-psychometriques/importer/'),
        formData,
        { headers: authHeaders },
      )
      const created = response.data?.created || []
      const rejected = response.data?.rejected || []
      setTests((previous) => [...created, ...previous])
      if (rejected.length) {
        setReport({
          title: 'Lignes ignorées lors de l’import',
          lines: rejected.map((item) => `Ligne ${item.ligne}${item.email ? ` (${item.email})` : ''} : ${item.message}`),
        })
      }
      const ignored = rejected.length ? ` ${rejected.length} ligne(s) ignorée(s), voir le détail ci-dessous.` : ''
      if (created.length) {
        setSuccess(`${created.length} candidat(s) importé(s) : un test a été généré pour chacun.${ignored}`)
      } else {
        setError(`Aucun candidat importé.${ignored}`)
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Impossible d’importer le fichier.'))
    } finally {
      setImporting(false)
    }
  }

  /**
   * Télécharge le fichier Excel de tous les tests, généré par le serveur
   * (Nom, Prénom, Email, Statut, Score, Date et lien vers le PDF des résultats).
   */
  async function exportExcel() {
    setError('')
    setSuccess('')
    setExporting(true)
    try {
      const response = await axios.get(
        buildApiUrl('/api/tests-psychometriques/exporter/'),
        { headers: authHeaders, responseType: 'blob' },
      )
      const disposition = response.headers['content-disposition'] || ''
      const filename = /filename="([^"]+)"/.exec(disposition)?.[1] || 'tests-psychometriques.xlsx'
      const url = URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      setSuccess('Export Excel téléchargé : cliquez sur « Ouvrir le PDF » pour voir les résultats d’un candidat.')
    } catch (requestError) {
      // En cas d'erreur, la réponse (JSON) arrive elle aussi sous forme de Blob.
      let message = 'Impossible d’exporter les tests.'
      try {
        const detail = JSON.parse(await requestError?.response?.data?.text())?.detail
        if (typeof detail === 'string' && detail) message = detail
      } catch {
        // Réponse illisible : message par défaut.
      }
      setError(message)
    } finally {
      setExporting(false)
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

  // Envoie le lien au candidat par email (SMTP) ; le serveur crée le lien si besoin.
  async function sendEmail(test) {
    setSendingId(test.id)
    setError('')
    setSuccess('')
    try {
      const response = await axios.post(
        buildApiUrl(`/api/tests-psychometriques/${test.id}/envoyer-email/`),
        {},
        { headers: authHeaders },
      )
      const updated = response.data
      setTests((previous) => previous.map((item) => (item.id === test.id ? updated : item)))
      setSuccess(`Email envoyé à ${updated.email} (lien valable jusqu’au ${formatDate(updated.token_expires_at)}).`)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Impossible d’envoyer l’email.'))
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
        {test.email_sent_at ? (
          <div className="test-list__statut-detail">Email envoyé le {formatDate(test.email_sent_at)}</div>
        ) : null}
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
        {test.statut === 'a_envoyer' || test.statut === 'envoye' ? (
          <Button
            variant="secondary"
            size="sm"
            className="test-list__action"
            icon={<Icon name="mail" size={14} />}
            disabled={busy}
            title={`Envoyer le lien à ${test.email} par email`}
            onClick={() => sendEmail(test)}
          >
            {busy ? 'Envoi…' : test.email_sent_at ? 'Renvoyer l’email' : 'Envoyer par email'}
          </Button>
        ) : null}
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

  const headers = [
    <input
      key="select-all"
      type="checkbox"
      className="test-list__checkbox"
      checked={allVisibleSelected}
      disabled={!selectableVisible.length || bulkSending}
      onChange={toggleAllVisible}
      aria-label="Sélectionner tous les tests non commencés"
      title="Sélectionner tous les tests non commencés"
    />,
    ...HEADERS,
  ]

  const rows = filteredTests.map((test) => ({
    key: test.id,
    className: selectedIds.has(test.id) && canReceiveEmail(test) ? 'test-list__row--selected' : '',
    cells: [
      {
        className: 'test-list__select-cell',
        content: (
          <input
            type="checkbox"
            className="test-list__checkbox"
            checked={selectedIds.has(test.id) && canReceiveEmail(test)}
            disabled={!canReceiveEmail(test) || bulkSending}
            onChange={() => toggleSelected(test.id)}
            aria-label={`Sélectionner ${test.prenom} ${test.nom}`}
            title={canReceiveEmail(test) ? '' : 'Test déjà commencé'}
          />
        ),
      },
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
        <div className="test-list__header-actions">
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.csv"
            hidden
            onChange={importFile}
          />
          <Button
            size="sm"
            variant="secondary"
            icon={<Icon name="export" size={14} />}
            disabled={importing}
            title="Fichier Excel (.xlsx) ou CSV avec les colonnes Prénom, Nom et Email"
            onClick={() => fileInputRef.current?.click()}
          >
            {importing ? 'Import…' : 'Importer'}
          </Button>
          <Button
            size="sm"
            variant="secondary"
            icon={<Icon name="file" size={14} />}
            disabled={exporting || !tests.some((test) => test.statut === 'repondu')}
            title="Télécharger en Excel les tests terminés (statut Répondu), avec le lien vers le PDF des résultats"
            onClick={exportExcel}
          >
            {exporting ? 'Export…' : 'Exporter tout'}
          </Button>
          <Button size="sm" variant="primary" icon={<Icon name="plus" size={14} />} onClick={openGenerate}>
            Générer un test
          </Button>
        </div>
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
      {report ? (
        <div className="import-report">
          <div className="import-report__header">
            <strong>{report.title}</strong>
            <button
              type="button"
              className="icon-button"
              onClick={() => setReport(null)}
              aria-label="Fermer le détail"
            >
              <Icon name="close" size={14} />
            </button>
          </div>
          <ul className="import-report__list">
            {report.lines.map((line, index) => (
              <li key={index}>{line}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {selectedTests.length || bulkSending ? (
        <div className="bulk-bar">
          <span className="bulk-bar__count">
            {bulkSending
              ? `Envoi en cours… ${bulkProgress.done} / ${bulkProgress.total}`
              : `${selectedTests.length} candidat(s) sélectionné(s)`}
          </span>
          {bulkSending ? (
            <div className="bulk-bar__track">
              <div
                className="bulk-bar__progress"
                style={{ width: `${bulkProgress.total ? (bulkProgress.done / bulkProgress.total) * 100 : 0}%` }}
              />
            </div>
          ) : (
            <div className="bulk-bar__actions">
              <Button variant="secondary" size="sm" onClick={() => setSelectedIds(new Set())}>
                Désélectionner
              </Button>
              <Button
                variant="primary"
                size="sm"
                icon={<Icon name="mail" size={14} />}
                onClick={() => setConfirmBulk(true)}
              >
                Envoyer par email ({selectedTests.length})
              </Button>
            </div>
          )}
        </div>
      ) : null}
      <DataTable
        headers={headers}
        rows={rows}
        emptyState={{
          icon: '📄',
          title: loading ? 'Chargement...' : 'Aucun test',
          text: loading
            ? 'Chargement des tests psychométriques.'
            : 'Cliquez sur « Générer un test » ou « Importer » pour créer les tests des candidats.',
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
      {confirmBulk ? (
        <ConfirmDialog
          title="Envoyer les liens par email"
          message={`Envoyer le lien du test par email à ${selectedTests.length} candidat(s) ? Les liens manquants seront générés (valables 7 jours).`}
          confirmLabel="Envoyer"
          confirmVariant="primary"
          onCancel={() => setConfirmBulk(false)}
          onConfirm={sendBulkEmails}
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
