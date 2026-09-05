import { useEffect, useState } from 'react'

import { getVendors } from './ops'

export function useVendors(cycle, sort = 'ota') {
  const [state, setState] = useState({ data: null, warning: null, loading: true, error: null })
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let cancelled = false
    setState({ data: null, warning: null, loading: true, error: null })
    getVendors(cycle, sort)
      .then((envelope) => {
        if (cancelled) return
        setState({ data: envelope.data, warning: envelope.warning, loading: false, error: null })
      })
      .catch((error) => {
        if (cancelled) return
        setState({ data: null, warning: null, loading: false, error })
      })
    return () => {
      cancelled = true
    }
  }, [cycle, sort, tick])

  return { ...state, refetch: () => setTick((value) => value + 1) }
}
