import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import type { HomeFeed } from '@shared/types'
import { getHomeFeed } from '@/api/home'
import {
  createHomeFeedRequestGate,
  type HomeFeedRequestGate,
} from './HomeFeedRequestGate'

interface HomeFeedContextValue {
  feed: HomeFeed | null
  loading: boolean
  error: unknown | null
  reload: () => Promise<void>
  setNotificationUnread: (count: number) => void
}

const HomeFeedContext = createContext<HomeFeedContextValue | null>(null)

export function HomeFeedProvider({ children }: { children: ReactNode }) {
  const [feed, setFeed] = useState<HomeFeed | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown | null>(null)
  const gateRef = useRef<HomeFeedRequestGate | null>(null)
  const initialRequestRef = useRef<Promise<HomeFeed> | null>(null)

  const applyRequest = useCallback(
    async (requestPromise: Promise<HomeFeed>, gate: HomeFeedRequestGate) => {
      const requestId = gate.begin()
      setLoading(true)
      setError(null)

      try {
        const nextFeed = await requestPromise
        gate.commit(requestId, () => {
          setFeed(nextFeed)
          setLoading(false)
        })
      } catch (nextError) {
        gate.commit(requestId, () => {
          setError(nextError)
          setLoading(false)
        })
      }
    },
    [],
  )

  const reload = useCallback(async () => {
    const gate = gateRef.current
    if (gate) {
      await applyRequest(getHomeFeed(), gate)
    }
  }, [applyRequest])

  const setNotificationUnread = useCallback((count: number) => {
    setFeed((current) => current ? {
      ...current,
      unread: { ...current.unread, notifications: Math.max(0, count) },
    } : current)
  }, [])

  useEffect(() => {
    const gate = createHomeFeedRequestGate()
    gateRef.current = gate
    if (!initialRequestRef.current) {
      initialRequestRef.current = getHomeFeed()
    }
    void applyRequest(initialRequestRef.current, gate)

    return () => {
      gate.dispose()
      if (gateRef.current === gate) {
        gateRef.current = null
      }
    }
  }, [applyRequest])

  const value = useMemo(
    () => ({ feed, loading, error, reload, setNotificationUnread }),
    [error, feed, loading, reload, setNotificationUnread],
  )

  return <HomeFeedContext.Provider value={value}>{children}</HomeFeedContext.Provider>
}

export function useHomeFeed(): HomeFeedContextValue {
  const context = useContext(HomeFeedContext)
  if (!context) {
    throw new Error('useHomeFeed must be used within a HomeFeedProvider')
  }
  return context
}
