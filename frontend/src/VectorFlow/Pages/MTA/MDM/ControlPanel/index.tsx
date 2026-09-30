
import IconCard from "../../../../../components/VectorFLOW/commons/VFCard/IconCard"
import { Container,PanelGrid, PanelGridWrapper } from "./styles"
import { useNavigate } from "react-router";
import ButtonCard from "../../../../../components/VectorFLOW/commons/VFCard/ButtonCard";
import { useDispatch } from "react-redux";
import { useGetMasterUIConfiguration } from "../../../../../VectorFlow/Services/MTA/MDM";
import { ADD_MASTER,TOGGLE_SELECT_MASTER_SCREEN,UPDATE_ACTIVE_MASTER, TOGGLE_UPLOAD_MODAL, RESET_STATE } from "../../../../../redux/actions/MDM";
import { mapMasterToMasterState } from "../../../../../helpers/utils";
import { useUserData } from "../../../../../context";
import { notifyError, notifyLoader } from "../../../../../helpers/notify";
import { toast } from "react-toastify";



const ControlPanel = ()=>{
    const navigate = useNavigate();

    const {user} = useUserData()

    const themeUi = user.user.theme_ui

    const {mutateAsync:getUiConfig} = useGetMasterUIConfiguration()

    const dispatch = useDispatch()
    const handleFNC = async()=>{
        try{
            notifyLoader("Loading FNC Data")
            const data = await getUiConfig('modify')
            const fncData:any = data.data.data.find((m:any)=>m.id==="13")
            if(fncData){
            dispatch(ADD_MASTER(mapMasterToMasterState([fncData])[0]))
            dispatch(TOGGLE_SELECT_MASTER_SCREEN(false))
            dispatch(UPDATE_ACTIVE_MASTER(0))     
            }
            dispatch(TOGGLE_UPLOAD_MODAL(false))
            navigate('/mta/master-data-management/control-panel/view-modify') 
            toast.dismiss()
        } catch(err:any){
            console.error(err)
            notifyError("Something Went Wrong")
        }
    }

    return (
        <Container>
            <PanelGridWrapper>
                <PanelGrid>
                    <IconCard iconOnMouseOut={'/assets/img/VectorFLOW/NMS/edit.svg'} iconOnMouseIn={'/assets/img/VectorFLOW/NMS/edit-hover.svg'} text={'View / Modify Records '}  onClick={()=>{
                        dispatch(TOGGLE_UPLOAD_MODAL(false))
                        dispatch(RESET_STATE())
                        navigate('/mta/master-data-management/control-panel/view-modify')
                    }} themeUi={themeUi}/>
                    <IconCard iconOnMouseOut={'/assets/img/VectorFLOW/NMS/add.svg'} iconOnMouseIn={'/assets/img/VectorFLOW/NMS/add-hover.svg'} text={'Add Records '} onClick={()=>{
                        dispatch(TOGGLE_UPLOAD_MODAL(false))
                        dispatch(RESET_STATE())
                        navigate('/mta/master-data-management/control-panel/add')
                    }} themeUi={themeUi}/>
                    <IconCard iconOnMouseOut={'/assets/img/VectorFLOW/NMS/delete.svg'} iconOnMouseIn={'/assets/img/VectorFLOW/NMS/delete-hover.svg'} text={'Delete Records '} onClick={()=>{
                        dispatch(RESET_STATE())
                        navigate('/mta/master-data-management/control-panel/delete')
                    }} themeUi={themeUi}/>
                </PanelGrid>
            </PanelGridWrapper>
            <PanelGridWrapper>
                <PanelGrid>
                    <ButtonCard opacity={"1"} text="Forced Norm Changes"  
                    onClick={() => {
                    handleFNC();
                    dispatch(RESET_STATE());
                }}  themeUi={themeUi}/>

                    <ButtonCard themeUi={themeUi} text="Phase-In Phase-Out" onClick={()=>console.log("clciked")}/>
                    <ButtonCard themeUi={themeUi} text="Seasonality" onClick={()=>console.log("clciked")}/> 
                </PanelGrid>
            </PanelGridWrapper>
        </Container>
    )
}

export default ControlPanel