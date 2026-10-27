/**
 * Input — atome de champ de saisie standard.
 * Props: toutes les props d'un <input>.
 */
export default function Input({ className = '', ...props }) {
  return <input className={`input-base ${className}`.trim()} {...props} />
}
