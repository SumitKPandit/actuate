import { useEffect, useState } from 'react';

import { getActions, getBriefing, getOverview } from './ops';

export function useOpsData(cycle) {
  const [state, setState] = useState({ data: null, warning: null, loading: true, error: null });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true }));
    Promise.all([getBriefing(cycle), getActions(cycle), getOverview(cycle)])
      .then(([briefing, actions, overview]) => {
        if (cancelled) return;
        const warning = briefing.warning ?? actions.warning ?? overview.warning ?? null;
        setState({ data: { briefing, actions, overview }, warning, loading: false, error: null });
      })
      .catch((err) => {
        if (cancelled) return;
        setState({ data: null, warning: null, loading: false, error: err });
      });
    return () => {
      cancelled = true;
    };
  }, [cycle, tick]);

  return { ...state, refetch: () => setTick((t) => t + 1) };
}
