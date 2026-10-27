export const theme = {
  colors: {
    background: 'linear-gradient(180deg, #f6fbf8 0%, #f1f7f4 100%)',
    surface: '#FFFFFF',
    surfaceAlt: '#f4fcf8',
    text: '#23362d',
    textMuted: '#718179',
    textSoft: '#718179',
    border: '#d8e9df',
    borderSoft: '#edf4ef',
    primary: '#008f5a',
    primaryDark: '#005132',
    primaryLight: '#def8eb',
    secondary: '#13b374',
    info: '#006b42',
    success: '#008f5a',
    successDark: '#005132',
    successLight: '#def8eb',
    warning: '#13b374',
    warningDark: '#005132',
    warningLight: '#def8eb',
    danger: '#c24141',
    dangerDark: '#9f3030',
    dangerLight: '#fff5f5',
    manager: '#006b42',
    managerLight: '#def8eb',
    hover: '#def8eb',
    overlay: 'rgba(0, 0, 0, 0.45)',
  },
  typography: {
    family: 'Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif',
    titleLg: '1.7rem',
    titleMd: '1.5rem',
    titleSm: '1.2rem',
    body: '0.9rem',
    bodySm: '0.85rem',
    caption: '0.82rem',
    captionXs: '0.75rem',
    weightRegular: '400',
    weightMedium: '500',
    weightSemibold: '600',
    weightBold: '700',
  },
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '0.75rem',
    lg: '1rem',
    xl: '1.5rem',
    xxl: '2rem',
    xxxl: '2.5rem',
  },
  radius: {
    sm: '6px',
    md: '8px',
    lg: '10px',
    xl: '12px',
    xxl: '16px',
    pill: '20px',
    round: '999px',
  },
  shadow: {
    header: '0 6px 20px rgba(0, 81, 50, 0.04)',
    sidebar: '2px 0 14px rgba(0, 81, 50, 0.06)',
    card: '0 14px 32px rgba(0, 81, 50, 0.08)',
    modal: '0 8px 32px rgba(0, 0, 0, 0.25)',
    focus: '0 0 0 4px rgba(19, 179, 116, 0.10)',
    button: '0 12px 22px rgba(0, 81, 50, 0.16)',
  },
  layout: {
    headerHeight: '70px',
    sidebarWidth: '240px',
    loginCardWidth: '400px',
    modalWidth: '660px',
    accentHeight: '4px',
  },
  motion: {
    fast: '0.2s ease',
    normal: '0.25s ease',
  },
  zIndex: {
    header: '100',
    modal: '9000',
  },
}

export const themeCssVars = `
:root {
  --font-family-base: ${theme.typography.family};
  --font-size-title-lg: ${theme.typography.titleLg};
  --font-size-title-md: ${theme.typography.titleMd};
  --font-size-title-sm: ${theme.typography.titleSm};
  --font-size-body: ${theme.typography.body};
  --font-size-body-sm: ${theme.typography.bodySm};
  --font-size-caption: ${theme.typography.caption};
  --font-size-caption-xs: ${theme.typography.captionXs};
  --font-weight-regular: ${theme.typography.weightRegular};
  --font-weight-medium: ${theme.typography.weightMedium};
  --font-weight-semibold: ${theme.typography.weightSemibold};
  --font-weight-bold: ${theme.typography.weightBold};

  --space-xs: ${theme.spacing.xs};
  --space-sm: ${theme.spacing.sm};
  --space-md: ${theme.spacing.md};
  --space-lg: ${theme.spacing.lg};
  --space-xl: ${theme.spacing.xl};
  --space-xxl: ${theme.spacing.xxl};
  --space-xxxl: ${theme.spacing.xxxl};

  --radius-sm: ${theme.radius.sm};
  --radius-md: ${theme.radius.md};
  --radius-lg: ${theme.radius.lg};
  --radius-xl: ${theme.radius.xl};
  --radius-xxl: ${theme.radius.xxl};
  --radius-pill: ${theme.radius.pill};
  --radius-round: ${theme.radius.round};

  --shadow-header: ${theme.shadow.header};
  --shadow-sidebar: ${theme.shadow.sidebar};
  --shadow-card: ${theme.shadow.card};
  --shadow-modal: ${theme.shadow.modal};
  --shadow-focus: ${theme.shadow.focus};
  --shadow-button: ${theme.shadow.button};

  --color-background: ${theme.colors.background};
  --color-surface: ${theme.colors.surface};
  --color-surface-alt: ${theme.colors.surfaceAlt};
  --color-text: ${theme.colors.text};
  --color-text-muted: ${theme.colors.textMuted};
  --color-text-soft: ${theme.colors.textSoft};
  --color-border: ${theme.colors.border};
  --color-border-soft: ${theme.colors.borderSoft};
  --color-primary: ${theme.colors.primary};
  --color-primary-dark: ${theme.colors.primaryDark};
  --color-primary-light: ${theme.colors.primaryLight};
  --color-secondary: ${theme.colors.secondary};
  --color-info: ${theme.colors.info};
  --color-success: ${theme.colors.success};
  --color-success-dark: ${theme.colors.successDark};
  --color-success-light: ${theme.colors.successLight};
  --color-warning: ${theme.colors.warning};
  --color-warning-dark: ${theme.colors.warningDark};
  --color-warning-light: ${theme.colors.warningLight};
  --color-danger: ${theme.colors.danger};
  --color-danger-dark: ${theme.colors.dangerDark};
  --color-danger-light: ${theme.colors.dangerLight};
  --color-manager: ${theme.colors.manager};
  --color-manager-light: ${theme.colors.managerLight};
  --color-hover: ${theme.colors.hover};
  --color-overlay: ${theme.colors.overlay};

  --color-primary-rgb: 0, 143, 90;
  --color-black-rgb: 0, 0, 0;

  --layout-header-height: ${theme.layout.headerHeight};
  --layout-sidebar-width: ${theme.layout.sidebarWidth};
  --layout-login-card-width: ${theme.layout.loginCardWidth};
  --layout-modal-width: ${theme.layout.modalWidth};
  --layout-accent-height: ${theme.layout.accentHeight};

  --motion-fast: ${theme.motion.fast};
  --motion-normal: ${theme.motion.normal};

  --z-header: ${theme.zIndex.header};
  --z-modal: ${theme.zIndex.modal};
}
`

export function injectThemeVars() {
  if (typeof document === 'undefined') return
  if (document.getElementById('enosisapp-theme-vars')) return

  const styleTag = document.createElement('style')
  styleTag.id = 'enosisapp-theme-vars'
  styleTag.textContent = themeCssVars
  document.head.appendChild(styleTag)
}
