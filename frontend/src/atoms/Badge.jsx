/**
 * Badge — atome d'affichage neutre.
 * Props:
 *   label : texte affiche
 *   tone  : 'warning' | 'success' | 'danger'
 */
export default function Badge({ label, tone = 'warning' }) {
  const normalizedLabel = String(label || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase()
  const pendingClass = normalizedLabel === 'en attente' ? ' badge--pending' : ''
  return <span className={`badge badge--${tone}${pendingClass}`}>{label}</span>
}
