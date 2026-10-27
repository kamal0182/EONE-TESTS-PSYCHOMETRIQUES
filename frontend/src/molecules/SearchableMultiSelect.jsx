import { useEffect, useRef, useState } from 'react'
import Icon from '../atoms/Icon.jsx'
import Badge from '../atoms/Badge.jsx'

function normalizeSearchValue(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
}

export default function SearchableMultiSelect({
  selectedIds = [],
  options = [],
  onChange,
  placeholder = 'Rechercher',
  disabled = false,
  getTone = () => 'warning',
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [highlightedIndex, setHighlightedIndex] = useState(0)
  const containerRef = useRef(null)

  const selectedOptions = options.filter((opt) => selectedIds.includes(opt.value))
  const availableOptions = options.filter((opt) => !selectedIds.includes(opt.value))

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const normalizedSearch = normalizeSearchValue(search)
  const filteredOptions = availableOptions.filter((option) =>
    normalizeSearchValue(option.label).includes(normalizedSearch),
  )

  const handleSelect = (option) => {
    onChange([...selectedIds, option.value])
    setSearch('')
    setHighlightedIndex(0)
  }

  const handleRemove = (id) => {
    onChange(selectedIds.filter((sid) => sid !== id))
  }

  const handleInputChange = (event) => {
    const nextValue = event.target.value
    setSearch(nextValue)
    setIsOpen(true)
    setHighlightedIndex(0)
  }

  const toggleOpen = () => {
    setIsOpen((current) => {
      const next = !current
      if (next) {
        setSearch('')
        setHighlightedIndex(0)
      }
      return next
    })
  }

  const handleKeyDown = (event) => {
    if (!isOpen && event.key === 'ArrowDown') {
      event.preventDefault()
      setIsOpen(true)
      setHighlightedIndex(0)
      return
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setHighlightedIndex((current) => Math.min(current + 1, filteredOptions.length - 1))
      return
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setHighlightedIndex((current) => Math.max(current - 1, 0))
      return
    }

    if (event.key === 'Enter' && isOpen) {
      event.preventDefault()
      const option = filteredOptions[highlightedIndex]
      if (option) {
        handleSelect(option)
      }
      return
    }

    if (event.key === 'Escape') {
      event.preventDefault()
      setIsOpen(false)
    }
  }

  const hasNoResults = isOpen && filteredOptions.length === 0

  return (
    <div ref={containerRef} className="searchable-multi-select">
      {/* Selected tags */}
      <div className="searchable-multi-select__tags" style={{ marginBottom: '8px' }}>
        {selectedOptions.map((option) => (
          <div
            key={option.value}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              marginRight: '6px',
              marginBottom: '4px',
            }}
          >
            <Badge label={option.label} tone={getTone(option.label)} />
            <button
              type="button"
              onClick={() => handleRemove(option.value)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '0 4px',
                fontSize: '14px',
                color: '#666',
              }}
              aria-label={`Supprimer ${option.label}`}
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      {/* Search input */}
      <div className="searchable-select__control">
        <input
          type="text"
          className="searchable-select__input"
          value={search}
          onChange={handleInputChange}
          onFocus={() => !isOpen && setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          aria-expanded={isOpen}
          aria-haspopup="listbox"
        />
        <button
          type="button"
          className="searchable-select__icon"
          onClick={toggleOpen}
          disabled={disabled}
          aria-label={isOpen ? 'Fermer la liste' : 'Ouvrir la liste'}
        >
          <Icon name={isOpen ? 'chevronUp' : 'chevronDown'} size={16} />
        </button>
      </div>

      {/* Dropdown menu */}
      {isOpen && (
        <div className="searchable-select__menu" role="listbox">
          {hasNoResults ? (
            <div className="searchable-select__no-results">Aucun résultat trouvé</div>
          ) : (
            filteredOptions.map((option, index) => (
              <button
                key={option.value}
                type="button"
                className={`searchable-select__option ${index === highlightedIndex ? 'is-highlighted' : ''}`}
                onClick={() => handleSelect(option)}
                onMouseEnter={() => setHighlightedIndex(index)}
                role="option"
                aria-selected={selectedIds.includes(option.value)}
              >
                {option.label}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}
