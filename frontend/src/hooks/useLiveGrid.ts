import { useCallback, useEffect, useRef, useState } from 'react';
import type { GridApi } from 'ag-grid-community';

export const isLiveGrid = (api?: GridApi | null): api is GridApi =>
  Boolean(api && !api.isDestroyed());

/** A loading report can replace its grid before the report itself unmounts. */
export default function useLiveGrid() {
  const [api, setApi] = useState<GridApi>();
  const current = useRef<GridApi>();
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      current.current = undefined;
    };
  }, []);

  const onGridReady = useCallback((event: { api: GridApi }) => {
    if (!mounted.current || !isLiveGrid(event.api)) return;
    current.current = event.api;
    setApi(event.api);
  }, []);
  const onGridPreDestroyed = useCallback((event: { api: GridApi }) => {
    // A late destroy event from the replaced grid must not clear its successor.
    if (current.current !== event.api) return;
    current.current = undefined;
    if (mounted.current) setApi(undefined);
  }, []);

  return { api, mounted, onGridReady, onGridPreDestroyed };
}
