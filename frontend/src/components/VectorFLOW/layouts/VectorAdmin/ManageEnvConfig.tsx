import { useNavigate } from "react-router"
import EnvConfigDrawer from "../../../../components/layouts/EnvConfigDrawer"

const ManageEnvConfig = () => {
  const navigate = useNavigate()

  return(
      <EnvConfigDrawer
          onClose={()=>navigate('/vector-admin')}
      />
  )
}

export default ManageEnvConfig