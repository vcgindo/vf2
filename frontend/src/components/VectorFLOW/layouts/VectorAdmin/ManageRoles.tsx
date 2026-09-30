import { useNavigate } from "react-router"
import UserRolesDrawer from "../../../../components/layouts/UserRolesDrawer"



const ManageRoles = ()=>{
    const navigate = useNavigate()

    return(
        <UserRolesDrawer
            onClose={()=>navigate('/vector-admin')}
        />
    )
}

export default ManageRoles