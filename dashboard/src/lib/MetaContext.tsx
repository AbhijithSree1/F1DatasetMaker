import { createContext, useContext, useMemo, type ReactNode } from 'react'
import { useData } from './useData'
import type { Driver, Meta, Team } from './types'

interface MetaContextValue {
  meta: Meta | null
  loading: boolean
  error: string | null
  driversById: Map<string, Driver>
  teamsById: Map<string, Team>
}

const MetaContext = createContext<MetaContextValue>({
  meta: null,
  loading: true,
  error: null,
  driversById: new Map(),
  teamsById: new Map(),
})

export function MetaProvider({ children }: { children: ReactNode }) {
  const { data, loading, error } = useData<Meta>('meta.json')

  const value = useMemo<MetaContextValue>(() => {
    const driversById = new Map((data?.drivers ?? []).map((d) => [d.driver_id, d]))
    const teamsById = new Map((data?.teams ?? []).map((t) => [t.team_id, t]))
    return { meta: data, loading, error, driversById, teamsById }
  }, [data, loading, error])

  return <MetaContext.Provider value={value}>{children}</MetaContext.Provider>
}

export function useMeta() {
  return useContext(MetaContext)
}
