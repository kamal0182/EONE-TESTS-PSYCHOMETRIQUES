import Label from '../atoms/Label.jsx'

/**
 * FormGroup — groupe visuel label + champ + hint.
 * Props:
 *   label    : string
 *   required : boolean
 *   hint     : node optionnel
 *   children : champ ou combinaison de champs
 */
export default function FormGroup({ label, required = false, hint = null, children }) {
  return (
    <div className="field-group">
      {label ? <Label required={required}>{label}</Label> : null}
      {children}
      {hint}
    </div>
  )
}
