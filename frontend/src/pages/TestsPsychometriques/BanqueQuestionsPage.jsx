import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import Button from '../../atoms/Button.jsx'
import Icon from '../../atoms/Icon.jsx'
import Input from '../../atoms/Input.jsx'
import Textarea from '../../atoms/Textarea.jsx'
import AlertMessage from '../../molecules/AlertMessage.jsx'
import FormGroup from '../../molecules/FormGroup.jsx'
import ConfirmDialog from '../../organisms/ConfirmDialog.jsx'
import ProcessOverview from '../../organisms/ProcessOverview.jsx'
import { buildApiUrl } from '../../config/api.js'

// Un niveau de la banque : endpoint, champ parent et formulaire d'édition.
const LEVELS = {
  coreValue: {
    label: 'core value',
    endpoint: '/api/core-values/',
    fields: [{ name: 'name', label: 'Nom de la core value', type: 'text' }],
  },
  version: {
    label: 'version',
    endpoint: '/api/core-value-versions/',
    parentKey: 'core_value_id',
    fields: [{ name: 'name', label: 'Nom de la version', type: 'text' }],
  },
  question: {
    label: 'question',
    endpoint: '/api/core-value-questions/',
    parentKey: 'version_id',
    fields: [
      { name: 'text', label: 'Question', type: 'textarea' },
      { name: 'ponderation', label: 'Pondération', type: 'number', min: 0, step: '0.01' },
    ],
  },
  answer: {
    label: 'réponse',
    endpoint: '/api/core-value-answers/',
    parentKey: 'question_id',
    fields: [
      { name: 'text', label: 'Réponse', type: 'textarea' },
      { name: 'percentage', label: 'Pourcentage (%)', type: 'number', min: 0, max: 100, step: '0.01' },
    ],
  },
}

function getErrorMessage(error, fallback) {
  const payload = error?.response?.data
  if (!payload) return error?.message || fallback
  if (typeof payload === 'string') return payload.includes('<html') ? fallback : payload
  if (payload.detail) return payload.detail
  const firstKey = Object.keys(payload)[0]
  const firstValue = firstKey ? payload[firstKey] : null
  if (Array.isArray(firstValue)) return firstValue.join(' ')
  if (typeof firstValue === 'string') return firstValue
  return fallback
}

function formatNumber(value) {
  const number = Number(value)
  return Number.isFinite(number)
    ? number.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
    : '-'
}

function Trace({ item }) {
  if (!item?.modifie_le) return null
  const date = new Date(item.modifie_le).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
  return (
    <span className='qb-trace'>
      Modifié par {item.modifie_par_nom || 'inconnu'} · {date}
    </span>
  )
}

function ItemActions({ onEdit, onDelete, addLabel, onAdd }) {
  return (
    <div className='qb-actions'>
      {onAdd ? (
        <Button size='sm' variant='secondary' icon={<Icon name='plus' size={14} />} onClick={onAdd}>
          {addLabel}
        </Button>
      ) : null}
      <Button size='sm' variant='secondary' onClick={onEdit}>Modifier</Button>
      <Button size='sm' variant='ghost-danger' onClick={onDelete}>Supprimer</Button>
    </div>
  )
}

function ItemFormModal({ form, isLoading, onClose, onSave }) {
  const level = LEVELS[form.level]
  const [values, setValues] = useState(() => Object.fromEntries(
    level.fields.map((field) => [field.name, form.item?.[field.name] ?? '']),
  ))
  const [error, setError] = useState('')

  function handleSubmit(event) {
    event.preventDefault()
    for (const field of level.fields) {
      const value = String(values[field.name] ?? '').trim()
      if (!value) {
        setError(`Le champ « ${field.label} » est obligatoire.`)
        return
      }
      if (field.type === 'number') {
        const number = Number(value.replace(',', '.'))
        if (!Number.isFinite(number) || number < field.min || (field.max !== undefined && number > field.max)) {
          setError(field.max !== undefined
            ? `« ${field.label} » doit être compris entre ${field.min} et ${field.max}.`
            : `« ${field.label} » doit être un nombre positif.`)
          return
        }
      }
    }
    setError('')
    const payload = Object.fromEntries(level.fields.map((field) => {
      const value = String(values[field.name]).trim()
      return [field.name, field.type === 'number' ? value.replace(',', '.') : value]
    }))
    onSave(payload)
  }

  return (
    <div className='modal-overlay' role='presentation' onClick={onClose}>
      <form
        className='modal qb-modal'
        role='dialog'
        aria-modal='true'
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <div className='modal__header'>
          <h2 className='modal__title'>
            {form.item ? 'Modifier' : 'Ajouter'} une {level.label}
          </h2>
          <button type='button' className='icon-button' onClick={onClose} disabled={isLoading} aria-label='Fermer'>
            <Icon name='close' />
          </button>
        </div>
        <div className='modal__body qb-modal__body'>
          {form.context ? <p className='qb-modal__context'>{form.context}</p> : null}
          {level.fields.map((field) => (
            <FormGroup key={field.name} label={field.label}>
              {field.type === 'textarea' ? (
                <Textarea
                  rows={3}
                  value={values[field.name]}
                  onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.value }))}
                  autoFocus={field === level.fields[0]}
                />
              ) : (
                <Input
                  type={field.type}
                  min={field.min}
                  max={field.max}
                  step={field.step}
                  value={values[field.name]}
                  onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.value }))}
                  autoFocus={field === level.fields[0]}
                />
              )}
            </FormGroup>
          ))}
          {form.item && form.level !== 'coreValue' && form.level !== 'version' ? (
            <p className='qb-modal__hint'>
              La modification s’applique aussi au calcul des scores des tests déjà passés.
            </p>
          ) : null}
          {error ? <p className='status-comment-dialog__error'>{error}</p> : null}
        </div>
        <div className='modal__footer'>
          <Button variant='secondary' onClick={onClose} disabled={isLoading}>Annuler</Button>
          <Button variant='primary' type='submit' disabled={isLoading}>
            {isLoading ? 'Sauvegarde...' : 'Enregistrer'}
          </Button>
        </div>
      </form>
    </div>
  )
}

export default function BanqueQuestionsPage({ user, roleTitle }) {
  const [data, setData] = useState({ coreValue: [], version: [], question: [], answer: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [expanded, setExpanded] = useState({})
  const [form, setForm] = useState(null)
  const [toDelete, setToDelete] = useState(null)
  const [saving, setSaving] = useState(false)

  const authConfig = useMemo(() => ({
    headers: user?.token ? { Authorization: 'Bearer ' + user.token } : {},
  }), [user?.token])

  async function loadAll() {
    setError('')
    try {
      const keys = Object.keys(LEVELS)
      const responses = await Promise.all(
        keys.map((key) => axios.get(buildApiUrl(LEVELS[key].endpoint), authConfig)),
      )
      setData(Object.fromEntries(keys.map((key, index) => [
        key,
        Array.isArray(responses[index].data) ? responses[index].data : [],
      ])))
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Impossible de charger la banque de questions.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAll()
  }, [authConfig])

  const childrenOf = useMemo(() => {
    const index = {}
    for (const key of ['version', 'question', 'answer']) {
      const parentKey = LEVELS[key].parentKey
      index[key] = {}
      for (const item of data[key]) {
        const parentId = String(item[parentKey])
        ;(index[key][parentId] ||= []).push(item)
      }
    }
    return (key, parentId) => index[key][String(parentId)] || []
  }, [data])

  function toggle(id) {
    setExpanded((current) => ({ ...current, [id]: !current[id] }))
  }

  async function saveForm(values) {
    const level = LEVELS[form.level]
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      if (form.item) {
        await axios.patch(buildApiUrl(`${level.endpoint}${form.item.id}/`), values, authConfig)
      } else {
        const payload = level.parentKey ? { ...values, [level.parentKey]: form.parentId } : values
        await axios.post(buildApiUrl(level.endpoint), payload, authConfig)
        if (form.parentId) setExpanded((current) => ({ ...current, [form.parentId]: true }))
      }
      setSuccess(`${level.label.charAt(0).toUpperCase()}${level.label.slice(1)} enregistrée.`)
      setForm(null)
      await loadAll()
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Impossible d’enregistrer.'))
      setForm(null)
    } finally {
      setSaving(false)
    }
  }

  async function confirmDelete() {
    const level = LEVELS[toDelete.level]
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      await axios.delete(buildApiUrl(`${level.endpoint}${toDelete.item.id}/`), authConfig)
      setSuccess(`${level.label.charAt(0).toUpperCase()}${level.label.slice(1)} supprimée.`)
      await loadAll()
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Impossible de supprimer.'))
    } finally {
      setSaving(false)
      setToDelete(null)
    }
  }

  function openAdd(level, parentId = null, context = '') {
    setForm({ level, parentId, context })
  }

  function openEdit(level, item, context = '') {
    setForm({ level, item, context })
  }

  function renderAnswers(question) {
    const answers = childrenOf('answer', question.id)
    return (
      <ul className='qb-answers'>
        {answers.map((answer) => (
          <li key={answer.id} className='qb-answer'>
            <span className='qb-answer__percentage'>{formatNumber(answer.percentage)} %</span>
            <div className='qb-answer__body'>
              <div>{answer.text}</div>
              <Trace item={answer} />
            </div>
            <ItemActions
              onEdit={() => openEdit('answer', answer, question.text)}
              onDelete={() => setToDelete({ level: 'answer', item: answer, title: answer.text })}
            />
          </li>
        ))}
        {!answers.length ? <li className='qb-empty'>Aucune réponse.</li> : null}
      </ul>
    )
  }

  function renderQuestions(version) {
    const questions = childrenOf('question', version.id)
    return (
      <div className='qb-questions'>
        {questions.map((question, index) => {
          const isOpen = expanded[question.id]
          const answerCount = childrenOf('answer', question.id).length
          return (
            <div key={question.id} className='qb-question'>
              <div className='qb-row'>
                <button type='button' className='qb-toggle' onClick={() => toggle(question.id)} aria-expanded={Boolean(isOpen)}>
                  <Icon name={isOpen ? 'chevronDown' : 'chevronRight'} size={16} />
                  <span className='qb-question__index'>Q{index + 1}</span>
                  <span className='qb-question__text'>{question.text}</span>
                </button>
                <span className='qb-pill'>Pondération {formatNumber(question.ponderation)}</span>
                <span className='qb-count'>{answerCount} réponse{answerCount > 1 ? 's' : ''}</span>
                <ItemActions
                  addLabel='Réponse'
                  onAdd={() => openAdd('answer', question.id, question.text)}
                  onEdit={() => openEdit('question', question, version.name)}
                  onDelete={() => setToDelete({ level: 'question', item: question, title: question.text })}
                />
              </div>
              <Trace item={question} />
              {isOpen ? renderAnswers(question) : null}
            </div>
          )
        })}
        {!questions.length ? <div className='qb-empty'>Aucune question dans cette version.</div> : null}
      </div>
    )
  }

  function renderVersions(coreValue) {
    const versions = childrenOf('version', coreValue.id)
    return (
      <div className='qb-versions'>
        {versions.map((version) => {
          const isOpen = expanded[version.id]
          const questions = childrenOf('question', version.id)
          const total = questions.reduce((sum, question) => sum + Number(question.ponderation || 0), 0)
          return (
            <div key={version.id} className='qb-version'>
              <div className='qb-row'>
                <button type='button' className='qb-toggle' onClick={() => toggle(version.id)} aria-expanded={Boolean(isOpen)}>
                  <Icon name={isOpen ? 'chevronDown' : 'chevronRight'} size={16} />
                  <strong>{version.name}</strong>
                </button>
                <span className='qb-count'>
                  {questions.length} question{questions.length > 1 ? 's' : ''} · total pondération {formatNumber(total)}
                </span>
                <ItemActions
                  addLabel='Question'
                  onAdd={() => openAdd('question', version.id, `${coreValue.name} · ${version.name}`)}
                  onEdit={() => openEdit('version', version, coreValue.name)}
                  onDelete={() => setToDelete({ level: 'version', item: version, title: version.name })}
                />
              </div>
              <Trace item={version} />
              {isOpen ? renderQuestions(version) : null}
            </div>
          )
        })}
        {!versions.length ? <div className='qb-empty'>Aucune version : cette core value bloque la génération des tests.</div> : null}
      </div>
    )
  }

  return (
    <ProcessOverview
      title='BANQUE DE QUESTIONS'
      breadcrumb={`${roleTitle} > Banque de questions`}
      cardIcon={<Icon name='folder' size={18} />}
      cardTitle='Paramétrage des tests psychométriques'
      action={(
        <Button size='sm' variant='primary' icon={<Icon name='plus' size={14} />} onClick={() => openAdd('coreValue')}>
          Ajouter une core value
        </Button>
      )}
    >
      <AlertMessage message={error} />
      <AlertMessage message={success} type='success' />
      <div className='qb-tree'>
        {data.coreValue.map((coreValue) => {
          const isOpen = expanded[coreValue.id]
          const versionCount = childrenOf('version', coreValue.id).length
          return (
            <section key={coreValue.id} className='qb-core-value'>
              <div className='qb-row'>
                <button type='button' className='qb-toggle' onClick={() => toggle(coreValue.id)} aria-expanded={Boolean(isOpen)}>
                  <Icon name={isOpen ? 'chevronDown' : 'chevronRight'} size={18} />
                  <span className='qb-core-value__name'>{coreValue.name}</span>
                </button>
                <span className='qb-count'>{versionCount} version{versionCount > 1 ? 's' : ''}</span>
                <ItemActions
                  addLabel='Version'
                  onAdd={() => openAdd('version', coreValue.id, coreValue.name)}
                  onEdit={() => openEdit('coreValue', coreValue)}
                  onDelete={() => setToDelete({ level: 'coreValue', item: coreValue, title: coreValue.name })}
                />
              </div>
              <Trace item={coreValue} />
              {isOpen ? renderVersions(coreValue) : null}
            </section>
          )
        })}
        {!data.coreValue.length ? (
          <div className='qb-empty'>
            {loading ? 'Chargement...' : 'Aucune core value. Commencez par en ajouter une.'}
          </div>
        ) : null}
      </div>

      {form ? (
        <ItemFormModal
          key={`${form.level}-${form.item?.id || 'new'}`}
          form={form}
          isLoading={saving}
          onClose={() => setForm(null)}
          onSave={saveForm}
        />
      ) : null}

      {toDelete ? (
        <ConfirmDialog
          title={`Supprimer la ${LEVELS[toDelete.level].label}`}
          message={`Supprimer « ${toDelete.title} » ainsi que tout son contenu ? Impossible si elle est déjà utilisée dans un test candidat.`}
          confirmLabel='Supprimer'
          isLoading={saving}
          onCancel={() => setToDelete(null)}
          onConfirm={confirmDelete}
        />
      ) : null}
    </ProcessOverview>
  )
}
