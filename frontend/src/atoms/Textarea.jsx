/**
 * Textarea — atome de zone de texte.
 * Props: toutes les props d'un <textarea>.
 */
export default function Textarea({ className = '', ...props }) {
  return <textarea className={`textarea-base ${className}`.trim()} {...props} />
}
