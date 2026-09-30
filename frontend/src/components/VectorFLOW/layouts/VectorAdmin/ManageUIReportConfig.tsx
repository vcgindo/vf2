import { useNavigate } from "react-router"
import UIReportConfigDrawer from "../../../../components/layouts/UIReportConfigDrawer"

const ManageUIReportConfig = () => {
  const navigate = useNavigate()

  return(
      <UIReportConfigDrawer
          onClose={()=>navigate('/vector-admin')}
      />
  )
}

export default ManageUIReportConfig