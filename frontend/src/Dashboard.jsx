import { useEffect, useState } from 'react'
import Button from './atoms/Button.jsx'
import Icon from './atoms/Icon.jsx'
import UserChip from './molecules/UserChip.jsx'
import Navbar from './organisms/Navbar.jsx'
import SidebarNav from './organisms/SidebarNav.jsx'
import DashboardLayout from './templates/DashboardLayout.jsx'
import TestsPsychometriquesPage from './pages/TestsPsychometriques/TestsPsychometriquesPage.jsx'
import BanqueQuestionsPage from './pages/TestsPsychometriques/BanqueQuestionsPage.jsx'
import { getInitials } from './utils/session.js'

const ROLE_TITLE = 'RECRUTEMENT'

const SECTIONS = [
  {
    title: ROLE_TITLE,
    items: [
      { key: 'tests_psychometriques', label: 'Tests psychométriques' },
      { key: 'banque_questions', label: 'Banque de questions' },
    ],
  },
]

const DEFAULT_VIEW = 'tests_psychometriques'
// La page active n'apparaît pas dans l'URL : elle est seulement mémorisée
// pour l'onglet, afin qu'un rechargement reste sur la même page.
const VIEW_STORAGE_KEY = 'eone-test-view'

function isKnownView(view) {
  return SECTIONS[0].items.some((item) => item.key === view)
}

function loadView() {
  try {
    const view = sessionStorage.getItem(VIEW_STORAGE_KEY)
    return isKnownView(view) ? view : DEFAULT_VIEW
  } catch {
    return DEFAULT_VIEW
  }
}

export default function Dashboard({ user, onLogout }) {
  const [view, setView] = useState(loadView)

  useEffect(() => {
    // Nettoie une ancienne URL du type /#banque_questions.
    if (window.location.hash) {
      window.history.replaceState(null, '', window.location.pathname + window.location.search)
    }
  }, [])

  function navigate(nextView) {
    try {
      sessionStorage.setItem(VIEW_STORAGE_KEY, nextView)
    } catch {
      // Stockage indisponible : seul le rechargement reviendra à la page par défaut.
    }
    setView(nextView)
  }

  const userName = user.nom || user.username

  return (
    <DashboardLayout
      header={(
        <Navbar
          brand={(
            <>
              <img src="/image_enosisapp.png?v=eone-20260611-new" alt="enosisapp Group Logo" />
              <span>eOne</span>
            </>
          )}
        >
          <UserChip
            initials={getInitials(userName)}
            primaryText={userName}
            secondaryText="Administrateur"
            accent
          />
          <Button
            variant="ghost-danger"
            onClick={onLogout}
            icon={<Icon name="logout" size={14} />}
            title="Déconnexion"
          >
            <span className="veille-header-logout-label">Déconnexion</span>
          </Button>
        </Navbar>
      )}
      sidebar={(
        <SidebarNav
          sections={SECTIONS}
          activeView={view}
          onNavigate={navigate}
          initiallyExpanded
          footer={(
            <UserChip
              initials={getInitials(userName)}
              primaryText={userName}
              variant="sidebar"
              accent
            />
          )}
        />
      )}
    >
      {view === 'banque_questions'
        ? <BanqueQuestionsPage user={user} roleTitle={ROLE_TITLE} />
        : <TestsPsychometriquesPage user={user} roleTitle={ROLE_TITLE} />}
    </DashboardLayout>
  )
}
