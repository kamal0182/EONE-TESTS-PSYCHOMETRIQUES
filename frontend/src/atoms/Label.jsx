/**
 * Label — atome de libelle de champ.
 * Props:
 *   children : texte du label
 *   required : booleen
 *   htmlFor  : id du champ cible
 */
export default function Label({ children, required = false, htmlFor }) {
  return (
    <label className="field-label" htmlFor={htmlFor}>
      {children}
      {required && <span className="field-label__required">*</span>}
    </label>
  )
}
