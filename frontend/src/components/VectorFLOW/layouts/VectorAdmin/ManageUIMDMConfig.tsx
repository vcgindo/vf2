import { useNavigate } from "react-router"
import UIMDMConfigDrawer from "../../../../components/layouts/UIMDMConfigDrawer"


const ManageUIMDMConfig = () => {
  const navigate = useNavigate()

  return(
      <UIMDMConfigDrawer
          onClose={()=>navigate('/vector-admin')}
      />
  )
}

export default ManageUIMDMConfig