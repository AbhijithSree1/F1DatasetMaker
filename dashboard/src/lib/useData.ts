import { useEffect, useState } from 'react'

interface DataState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

const cache = new Map<string, unknown>()

export function useData<T>(path: string): DataState<T> {
  const [state, setState] = useState<DataState<T>>(() => {
    if (cache.has(path)) return { data: cache.get(path) as T, loading: false, error: null }
    return { data: null, loading: true, error: null }
  })

  useEffect(() => {
    if (cache.has(path)) return
    let cancelled = false

    fetch(`${import.meta.env.BASE_URL}data/${path}`)
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
        return res.json()
      })
      .then((json: T) => {
        cache.set(path, json)
        if (!cancelled) setState({ data: json, loading: false, error: null })
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ data: null, loading: false, error: err.message })
      })

    return () => {
      cancelled = true
    }
  }, [path])

  return state
}
