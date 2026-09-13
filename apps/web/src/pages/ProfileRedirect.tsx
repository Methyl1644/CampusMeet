import { Navigate, useSearchParams } from 'react-router-dom'

export function personalRedirectTarget(search: URLSearchParams) {
  if (search.get('tab') === 'events') return '/my/activities'
  if (search.get('tab') === 'groups') return '/my/groups'
  if (search.get('view') === 'notifications') return '/notifications'
  if (search.get('view') === 'settings') return '/settings'
  return '/users/me'
}

export default function ProfileRedirect() {
  const [search] = useSearchParams()
  return <Navigate to={personalRedirectTarget(search)} replace />
}
