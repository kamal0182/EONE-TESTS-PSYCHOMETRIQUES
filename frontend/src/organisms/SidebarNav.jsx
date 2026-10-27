import { useState } from 'react'
import Icon from '../atoms/Icon.jsx'

/**
 * Pages reachable from a list of sidebar items, with groups flattened.
 * An item with ``children`` is a sub-group: only its children are pages.
 */
export function flattenSidebarItems(items = []) {
  return items.flatMap((item) => (item.children ? flattenSidebarItems(item.children) : [item]))
}

/**
 * SidebarNav — navigation laterale controlee par la page.
 * Props:
 *   sections       : [{ title, items: [{ key, label } | { key, label, children: [{ key, label }] }] }]
 *                    an item with ``children`` is a collapsible sub-group (not a page itself)
 *   activeView     : vue active
 *   onNavigate     : callback(view)
 *   footer         : zone libre injectee en pied
 *   initiallyExpanded : sections ouvertes au chargement
 */
export default function SidebarNav({
  sections,
  activeView,
  onNavigate,
  badgeCounts = {},
  footer = null,
  initiallyExpanded = false,
}) {
  const [expanded, setExpanded] = useState(() => {
    const init = {}
    sections.forEach((s) => {
      init[s.title] = initiallyExpanded
    })
    return init
  })
  // Sub-groups start open when they hold the active page, closed otherwise.
  const [expandedGroups, setExpandedGroups] = useState({})

  const toggleSection = (title) => {
    setExpanded((prev) => ({ ...prev, [title]: !prev[title] }))
  }

  const countBadges = (items) => flattenSidebarItems(items)
    .reduce((sum, item) => sum + (badgeCounts[item.key] || 0), 0)

  const renderPageItem = (item, extraClass = '') => (
    <li key={item.key}>
      <button
        type="button"
        className={`sidebar-item${extraClass}${activeView === item.key ? ' is-active' : ''}`}
        onClick={() => onNavigate(item.key)}
      >
        <span className="sidebar-item-label">{item.label}</span>
        {badgeCounts[item.key] > 0 && (
          <span className="sidebar-item-badge">{badgeCounts[item.key]}</span>
        )}
      </button>
    </li>
  )

  const renderGroup = (group) => {
    const holdsActive = group.children.some((child) => child.key === activeView)
    const isOpen = expandedGroups[group.key] ?? holdsActive
    const groupTotal = countBadges(group.children)
    return (
      <li key={group.key} className="sidebar-group">
        <button
          type="button"
          className={`sidebar-item sidebar-group-toggle${holdsActive && !isOpen ? ' is-active' : ''}`}
          onClick={() => setExpandedGroups((prev) => ({ ...prev, [group.key]: !isOpen }))}
          aria-expanded={isOpen}
        >
          <span className="sidebar-item-label">{group.label}</span>
          {groupTotal > 0 && !isOpen && (
            <span className="sidebar-item-badge">{groupTotal}</span>
          )}
          <span className="sidebar-section-chevron" aria-hidden="true">
            <Icon name={isOpen ? 'chevronDown' : 'chevronRight'} size={14} />
          </span>
        </button>
        {isOpen && (
          <ul className="sidebar-menu sidebar-submenu">
            {group.children.map((child) => renderPageItem(child, ' sidebar-subitem'))}
          </ul>
        )}
      </li>
    )
  }

  return (
    <aside className="sidebar">
      <div>
        {sections.map((section) => {
          const sectionTotal = countBadges(section.items)
          return (
          <div className="sidebar-section" key={section.title}>
            <button
              type="button"
              className="sidebar-section-title"
              onClick={() => toggleSection(section.title)}
              aria-expanded={expanded[section.title]}
            >
              <span className="sidebar-section-title-text">{section.title}</span>
              {sectionTotal > 0 && (
                <span className="sidebar-section-badge">{sectionTotal}</span>
              )}
              <span className="sidebar-section-chevron" aria-hidden="true">
                <Icon name={expanded[section.title] ? 'chevronDown' : 'chevronRight'} size={14} />
              </span>
            </button>
            {expanded[section.title] && (
              <ul className="sidebar-menu">
                {section.items.map((item) => (item.children ? renderGroup(item) : renderPageItem(item)))}
              </ul>
            )}
          </div>
          )
        })}
      </div>

      <div className="sidebar-footer">
        {footer}
      </div>
    </aside>
  )
}
