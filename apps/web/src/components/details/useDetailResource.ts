import { useCallback, useEffect, useRef, useState } from 'react'

type DetailLoader<T> = (id: string, signal?: AbortSignal) => Promise<T>

export function useRouteGeneration(routeKey: string) {
  const owner = useRef({ key: routeKey, generation: 1 })
  if (owner.current.key !== routeKey) {
    owner.current = { key: routeKey, generation: owner.current.generation + 1 }
  }
  return owner
}

export function useDetailResource<T>(id: string, load: DetailLoader<T>) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const requestGeneration = useRef(0)

  useEffect(() => {
    if (!id) {
      setData(null)
      setLoading(false)
      setError(true)
      return
    }

    const controller = new AbortController()
    const generation = ++requestGeneration.current
    setData(null)
    setLoading(true)
    setError(false)

    load(id, controller.signal)
      .then((result) => {
        if (generation !== requestGeneration.current || controller.signal.aborted) return
        setData(result)
      })
      .catch(() => {
        if (generation !== requestGeneration.current || controller.signal.aborted) return
        setError(true)
      })
      .finally(() => {
        if (generation !== requestGeneration.current || controller.signal.aborted) return
        setLoading(false)
      })

    return () => controller.abort()
  }, [attempt, id, load])

  const retry = useCallback(() => setAttempt((value) => value + 1), [])

  return { data, setData, loading, error, retry }
}
