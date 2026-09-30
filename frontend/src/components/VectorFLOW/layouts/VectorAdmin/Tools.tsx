import { useNavigate } from "react-router"
import IconCard from "../../commons/VFCard/IconCard"
import { PanelGrid } from "../SelectMaster/styles"
import {  ToolsWrapper } from "./styles"
import { useAuth } from "./useAuth"
import Spinner from "../../../../components/commons/Spinner"
import { useUserData } from "../../../../context"


const Tools = ()=>{

    const navigate = useNavigate()
    const { user } = useUserData();
    const isAdmin = user?.user?.is_admin;
    const isPermissionsManager  = user?.roles?.permission.includes("PermissionsManager");
    
    return(
        <ToolsWrapper>
            <PanelGrid style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)', 
                gap: '20px', 
                maxWidth: 900 
            }}>
            { 
             isAdmin &&   
             <>
             <div>
                    <IconCard
                        text="Manage Roles"
                        iconOnMouseIn="/assets/img/VectorFLOW/NMS/edit.svg"
                        iconOnMouseOut="/assets/img/VectorFLOW/NMS/edit.svg"
                        onClick={()=>navigate('/vector-admin/manage-roles')}
                        themeUi="NOIRFUSION"
                    />
                </div>
                <div>
                    <IconCard
                        text="Manage URLs"
                        iconOnMouseIn="/assets/img/VectorFLOW/NMS/edit.svg"
                        iconOnMouseOut="/assets/img/VectorFLOW/NMS/edit.svg"
                        onClick={()=>navigate('/vector-admin/manage-urls')}
                        themeUi="NOIRFUSION"
                    />
                </div>
                <div>
                    <IconCard
                        text="Manage Configuration"
                        iconOnMouseIn="/assets/img/VectorFLOW/NMS/edit.svg"
                        iconOnMouseOut="/assets/img/VectorFLOW/NMS/edit.svg"
                        onClick={()=>navigate('/vector-admin/manage-env-configuration')}
                        themeUi="NOIRFUSION"
                    />
                </div>
                <div>
                    <IconCard
                        text="Manage UI Report Configuration"
                        iconOnMouseIn="/assets/img/VectorFLOW/NMS/edit.svg"
                        iconOnMouseOut="/assets/img/VectorFLOW/NMS/edit.svg"
                        onClick={()=>navigate('/vector-admin/manage-ui-report-configuration')}
                        themeUi="NOIRFUSION"
                    />
                </div>
                <div>
                    <IconCard
                        text="Manage UI MDM Configuration"
                        iconOnMouseIn="/assets/img/VectorFLOW/NMS/edit.svg"
                        iconOnMouseOut="/assets/img/VectorFLOW/NMS/edit.svg"
                        onClick={()=>navigate('/vector-admin/manage-ui-mdm-configuration')}
                        themeUi="NOIRFUSION"
                    />
                </div>
                </>
                }
            { 
             isPermissionsManager  &&   
             <div>
                    <IconCard
                        text="Manage Permissions"
                        iconOnMouseIn="/assets/img/VectorFLOW/NMS/edit.svg"
                        iconOnMouseOut="/assets/img/VectorFLOW/NMS/edit.svg"
                        onClick={()=>navigate('/vector-admin/manage-permissions')}
                        themeUi="NOIRFUSION"
                    />
                </div>
            }
            </PanelGrid>
        </ToolsWrapper>
    )
}

export default Tools