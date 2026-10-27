import MetricCard from '../molecules/MetricCard.jsx'

/**
 * KpiGrid — grille generique de cartes metriques.
 * Props:
 *   items : [{ label, value, tone }]
 */
export default function KpiGrid({ items }) {
  return (
    <div className="kpi-grid">
      {items.map((item) => (
        <MetricCard
          key={`${item.label}-${item.tone}`}
          label={item.label}
          value={item.value}
          tone={item.tone}
        />
      ))}
    </div>
  )
}
