/**
 * MetricCard — carte KPI issue des stats du dashboard.
 * Props:
 *   label : libelle affiche
 *   value : valeur numerique
 *   tone  : 'blue' | 'orange' | 'green' | 'red'
 */
export default function MetricCard({ label, value, tone = 'blue' }) {
  return (
    <div className={`metric-card metric-card--${tone}`}>
      <div className="metric-card__label">{label}</div>
      <div className="metric-card__value">{value}</div>
    </div>
  )
}
