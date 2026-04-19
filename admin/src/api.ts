const configuredApiBase = (import.meta.env.VITE_API_URL as string | undefined)?.trim()

export const API_BASE_URL = (configuredApiBase && configuredApiBase.replace(/\/+$/, '')) || window.location.origin

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}
