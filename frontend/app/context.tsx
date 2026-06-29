'use client'
import { createContext, useContext } from 'react'

export interface Domain {
  id: number
  slug: string
  name: string
  label: string
  entity_label: string
}

export interface AppCtx {
  domain: Domain | null
  domains: Domain[]
  setDomain: (d: Domain) => void
}

export const AppContext = createContext<AppCtx>({
  domain: null,
  domains: [],
  setDomain: () => {},
})

export const useApp = () => useContext(AppContext)
