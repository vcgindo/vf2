import { SCMenu, SCMenuList, SCMenuItem } from './styles'

interface ListItemInputProps {
  data: any
  onClickItem: any
}
const ListItemInput = ({ data, onClickItem }: ListItemInputProps) => {
  return (
    <SCMenu>
      <SCMenuList>
        {data?.map((item: any, index: number) => (
          <SCMenuItem key={index} onClick={(e) => onClickItem(e)}>
            {item}
          </SCMenuItem>
        ))}

        {data?.length === 0 && (
          <SCMenuItem>
            <div style={{ width: '155px' }}>No Data</div>
          </SCMenuItem>
        )}
      </SCMenuList>
    </SCMenu>
  )
}

export default ListItemInput
