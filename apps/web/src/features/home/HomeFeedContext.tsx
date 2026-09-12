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

interface HomeFeedContextValue {
  feed: HomeFeed | null
  loading: boolean
  error: unknown | null
  reload: () => Promise<void>
}

const HomeFeedContext = createContext<HomeFeedContextValue | null>(null)

export function HomeFeedProvider({ children }: { children: ReactNode }) {
  const [feed, setFeed] = useState<HomeFeed | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown | null>(null)
  const mountedRef = useRef(false)
  const requestRef = useRef(0)
  const initialRequestRef = useRef<Promise<HomeFeed> | null>(null)

  const applyRequest = useCallback(async (requestPromise: Promise<HomeFeed>) => {
    const request = ++requestRef.current
    setLoading(true)
    setError(null)

    try {
      const nextFeed = await requestPromise
      if (mountedRef.current && request === requestRef.current) {
        setFeed(nextFeed)
      }
    } catch (nextError) {
      if (mountedRef.current && request === requestRef.current) {
        setError(nextError)
      }
    } finally {
      if (mountedRef.current && request === requestRef.current) {
        setLoading(false)
      }
    }
  }, [])

  const reload = useCallback(
    async () => applyRequest(getHomeFeed()),
    [applyRequest],
  )

  useEffect(() => {
    mountedRef.current = true
    if (!initialRequestRef.current) {
      initialRequestRef.current = getHomeFeed()
    }
    void applyRequest(initialRequestRef.current)

    return () => {
      mountedRef.current = false
      requestRef.current += 1
    }
  }, [applyRequest])

  const value = useMemo(
    () => ({ feed, loading, error, reload }),
    [error, feed, loading, reload],
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
