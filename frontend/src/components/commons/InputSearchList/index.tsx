import { type ChangeEvent } from 'react'
import { SCSearchText, SCIconLocation } from './styles'

interface InputSearchListProps {
  placeholder: string
  searchText: string
  srcIcon: string
  handleChangeText: (event: ChangeEvent<HTMLInputElement>) => void
}
const InputSearchList = ({
  placeholder,
  searchText,
  srcIcon,
  handleChangeText
}: InputSearchListProps) => {
  return (
    <>
      <SCIconLocation className="icon_location" src={srcIcon} />
      <SCSearchText>
        <input
          placeholder={placeholder}
          aria-label="Search components"
          id={'search-' + placeholder}
          value={searchText}
          type="text"
          onChange={handleChangeText}
        />
      </SCSearchText>
    </>
  )
}

export default InputSearchList
