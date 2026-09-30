import { type ChangeEvent } from 'react'

interface SearchInputProps {
  searchText: string
  handleChangeText: (event: ChangeEvent<HTMLInputElement>) => void
}
const SearchInput = ({ searchText, handleChangeText }: SearchInputProps) => {
  return (
    <input
      placeholder="Search"
      aria-label="Search components"
      id="search"
      role="combobox"
      value={searchText}
      type="text"
      onChange={handleChangeText}
    />
  )
}

export default SearchInput
