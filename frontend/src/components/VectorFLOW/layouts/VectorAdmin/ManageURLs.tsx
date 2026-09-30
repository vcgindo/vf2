import { useNavigate } from "react-router"
import UserURLsDrawer from "../../../../components/layouts/UserURLsDrawer"



const ManageURLs = ()=>{
    const navigate = useNavigate()

    return(
        <UserURLsDrawer
            onClose={()=>navigate('/vector-admin')}
        />
    )
}

export default ManageURLs