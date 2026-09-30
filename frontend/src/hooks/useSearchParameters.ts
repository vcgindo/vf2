import { useSearchParams } from 'react-router-dom'
import { useDebouncedSearch } from './index'
import { useState, useCallback, type ChangeEvent } from 'react'
import { sanitizeUserSearchText } from '../helpers/utils'

const useSearchParameters = () => {
  const [searchParams, setSearchParams] = useSearchParams()

  const defaultSearchText = searchParams.get('search') || ''
  const [searchText, setSearchText] = useState<string>(defaultSearchText) // value for search box

  const [debouncedSearchText, setDebouncedSearchText] = useState(searchText) // value for API call

  const _debouncedSearch = useDebouncedSearch(
    useCallback(
      (search: string) => {
        setDebouncedSearchText(search)

        if (search) {
          searchParams.set('search', search)
        } else {
          searchParams.delete('search')
        }

        setSearchParams(searchParams)
      },
      [searchParams, setSearchParams]
    )
  )

  const handleSearchTextChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const search = sanitizeUserSearchText(event.target.value)
      setSearchText((prevSearch: string) => {
        if (search !== prevSearch) {
          _debouncedSearch(search)
        }
        return search
      })
    },
    [_debouncedSearch]
  )

  return {
    handleSearchTextChange,
    debouncedSearchText,
    searchText
  }
}

export default useSearchParameters
