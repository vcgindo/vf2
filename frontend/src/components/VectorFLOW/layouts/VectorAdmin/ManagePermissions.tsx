import { useNavigate } from "react-router"
import PermissionsDrawer from "../../../../components/layouts/PermissionsDrawer"

const ManagePermissions = () => {
  const navigate = useNavigate()

  return(
      <PermissionsDrawer
          onClose={()=>navigate('/vector-admin')}
      />
  )
}

export default ManagePermissions