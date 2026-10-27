export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export function buildApiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`

  if (!API_BASE_URL) {
    return normalizedPath
  }

  const normalizedBaseUrl = API_BASE_URL.replace(/\/$/, '')
  if (normalizedPath.startsWith(normalizedBaseUrl)) {
    return normalizedPath
  }

  return `${normalizedBaseUrl}${normalizedPath}`
}
