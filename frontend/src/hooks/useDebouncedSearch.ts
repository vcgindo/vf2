import _ from 'lodash'
import { useEffect, useMemo } from 'react'

const useDebouncedSearch = (
  searchFn: (...args: any) => void,
  timeout = 300
) => {
  const onDebouncedSearch = useMemo(
    () => _.debounce(searchFn, timeout),
    [searchFn, timeout]
  )

  useEffect(() => {
    return () => {
      onDebouncedSearch.cancel()
    }
  }, [onDebouncedSearch])

  return onDebouncedSearch
}

export default useDebouncedSearch
