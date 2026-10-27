import Button from '../atoms/Button.jsx'
import Input from '../atoms/Input.jsx'
import Select from '../atoms/Select.jsx'
import FormGroup from './FormGroup.jsx'
import SearchableMultiSelect from './SearchableMultiSelect.jsx'

/**
 * MarketingHeaderFilters — panneau de filtres réutilisable pour les pages marketing.
 *
 * Props:
 *   searchValue              : string
 *   onSearchChange           : fn(nextValue)
 *   searchPlaceholder        : string
 *   dateFromValue            : string
 *   onDateFromChange         : fn(nextValue)
 *   dateToValue              : string
 *   onDateToChange           : fn(nextValue)
 *   confidentialiteValue     : string
 *   onConfidentialiteChange  : fn(nextValue)
 *   confidentialiteOptions   : string[]
 *   marqueValue              : string
 *   onMarqueChange           : fn(nextValue)
 *   marqueOptions            : string[]
 *   selectedTags             : string[]
 *   onTagsChange             : fn(nextValues)
 *   tagOptions               : [{ value, label }]
 *   onResetFilters           : fn | null
 *   showFilters              : boolean
 */
export default function MarketingHeaderFilters({
  searchValue = '',
  onSearchChange,
  searchPlaceholder = 'Rechercher',
  dateFromValue = '',
  onDateFromChange,
  dateToValue = '',
  onDateToChange,
  confidentialiteValue = '',
  onConfidentialiteChange,
  confidentialiteOptions = [],
  marqueValue = '',
  onMarqueChange,
  marqueOptions = [],
  selectedTags = [],
  onTagsChange,
  tagOptions = [],
  onResetFilters = null,
  showFilters = true,
}) {
  const showMarqueFilter = Boolean(onMarqueChange || marqueValue || marqueOptions.length)
  const hasActiveFilters = Boolean(
    searchValue
      || dateFromValue
      || dateToValue
      || confidentialiteValue
      || marqueValue
      || (selectedTags && selectedTags.length),
  )

  return (
    <section className="course-filters-panel marketing-header-filters" aria-label="Filtres marketing">
      <div className="marketing-header-filters__full">
        <FormGroup label="Recherche">
          <Input
            type="text"
            value={searchValue}
            onChange={(event) => onSearchChange?.(event.target.value)}
            placeholder={searchPlaceholder}
          />
        </FormGroup>
      </div>

      {showFilters ? (
      <div className="marketing-header-filters__full course-filters-grid">
        <FormGroup label="Du">
          <Input
            type="date"
            value={dateFromValue}
            onChange={(event) => onDateFromChange?.(event.target.value)}
          />
        </FormGroup>

        <FormGroup label="Au">
          <Input
            type="date"
            value={dateToValue}
            onChange={(event) => onDateToChange?.(event.target.value)}
          />
        </FormGroup>

        <FormGroup label="Confidentialité">
          <Select
            value={confidentialiteValue}
            onChange={(event) => onConfidentialiteChange?.(event.target.value)}
          >
            <option value="">Toutes les confidentialités</option>
            {confidentialiteOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </Select>
        </FormGroup>

        {showMarqueFilter ? (
          <FormGroup label="Marque">
            <Select
              value={marqueValue}
              onChange={(event) => onMarqueChange?.(event.target.value)}
            >
              <option value="">Toutes les marques</option>
              {marqueOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </Select>
          </FormGroup>
        ) : (
          <FormGroup label="Tags">
            <SearchableMultiSelect
              selectedIds={selectedTags}
              options={tagOptions}
              onChange={onTagsChange}
              placeholder="Rechercher"
            />
          </FormGroup>
        )}
      </div>
      ) : null}

      {onResetFilters && hasActiveFilters ? (
        <div className="marketing-header-filters__full marketing-header-filters__actions">
          <Button variant="secondary" size="sm" onClick={onResetFilters}>
            Réinitialiser
          </Button>
        </div>
      ) : null}
    </section>
  )
}
