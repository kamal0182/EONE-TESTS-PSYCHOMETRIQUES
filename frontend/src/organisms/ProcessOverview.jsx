import PageHeader from '../molecules/PageHeader.jsx'
import KpiGrid from './KpiGrid.jsx'
import TableCard from './TableCard.jsx'

/**
 * ProcessOverview — bloc principal titre + metriques + tableau.
 * Props:
 *   title       : titre de page
 *   breadcrumb  : fil d'ariane
 *   metrics     : liste de metriques optionnelle
 *   cardIcon    : icone du tableau
 *   cardTitle   : titre du tableau
 *   headerMiddle: node optionnel dans le header de carte
 *   action      : action du header de carte
 *   footer      : contenu sous le tableau
 *   children    : tableau
 */
export default function ProcessOverview({
  title,
  breadcrumb,
  metrics = null,
  beforeTable = null,
  cardIcon,
  cardTitle,
  headerMiddle = null,
  action = null,
  footer = null,
  children,
}) {
  return (
    <>
      <PageHeader title={title} breadcrumb={breadcrumb} />
      {metrics?.length ? <KpiGrid items={metrics} /> : null}
      {beforeTable}
      <TableCard icon={cardIcon} title={cardTitle} middle={headerMiddle} actions={action} footer={footer}>
        {children}
      </TableCard>
    </>
  )
}
