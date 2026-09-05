import { useEffect, useState } from 'react';

import { ApiError, getBriefing } from './ops';

const DEFAULT_CYCLE = '2026-06-H1';

export function useCycle(initialCycle = DEFAULT_CYCLE) {
  const [cycle, setCycle] = useState(initialCycle || DEFAULT_CYCLE);
  const [cycles, setCycles] = useState(null);

  useEffect(() => {
    if (cycles !== null) return;
    let cancelled = false;
    getBriefing(cycle).then(
      () => {},
      (err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          const vc = err.body?.valid_cycles;
          if (Array.isArray(vc) && vc.length > 0) {
            setCycle(vc[0]);
            setCycles(vc);
          } else {
            setCycles([]);
          }
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  return { cycle, cycles, setCycle };
}
