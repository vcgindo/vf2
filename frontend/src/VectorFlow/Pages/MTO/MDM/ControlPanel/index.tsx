import IconCard from "../../../../../components/VectorFLOW/commons/VFCard/IconCard"
import { Container,PanelGrid, PanelGridWrapper } from "./styles"
import { useNavigate } from "react-router";

// import ButtonCard from "../../../../../components/VectorFLOW/commons/VFCard/ButtonCard";
// import { useDispatch } from "react-redux";
// import { useGetMasterUIConfiguration } from "../../../../../VectorFlow/Services/MTA/MDM";
// import { ADD_MASTER,TOGGLE_SELECT_MASTER_SCREEN,UPDATE_ACTIVE_MASTER } from "../../../../../redux/actions/MDM";
// import { mapMasterToMasterState } from "../../../../../helpers/utils";


import { useUserData } from "../../../../../context";
import { useDispatch } from "react-redux";
import { RESET_MTO_STATE, SET_BUFFER_INITIAL_DATA, SET_BUFFER_MODIFY_DATA, SET_CCR_INITIAL_DATA, SET_CCR_MODIFY_DATA, SET_POOGI_INITIAL_DATA, SET_POOGI_MODIFY_DATA } from "../../../../../redux/actions/MTO";
import { ADD_FILTER, FILL_MASTERS, REMOVE_ALL_FILTERS, TOGGLE_SELECT_MASTER_SCREEN, TOGGLE_UPLOAD_MODAL, UPDATE_COLDEFS, UPDATE_PROGRESS_STATE, UPDATE_ROW_DATA } from "../../../../../redux/actions/MDM";



const MTOControlPanel = ()=>{
    const navigate = useNavigate();
 const dispatch = useDispatch();
    const {user} = useUserData()

    const themeUi = user.user.theme_ui

    // const {mutateAsync:getUiConfig} = useGetMasterUIConfiguration()

    // const dispatch = useDispatch()
    // const handleFNC = async()=>{
    //     const data = await getUiConfig('modify')
    //     const fncData:any = data.data.data.find((m:any)=>m.id==="13")
    //     if(fncData){
    //       dispatch(ADD_MASTER(mapMasterToMasterState([fncData])[0]))
    //       dispatch(TOGGLE_SELECT_MASTER_SCREEN(false))
    //       dispatch(UPDATE_ACTIVE_MASTER(0))     
    //     }
    //     navigate('/mto/master-data-management/control-panel/view-modify')   
    // }

    const clearVal = ()=>{
      dispatch(RESET_MTO_STATE());
      dispatch(UPDATE_PROGRESS_STATE("default"));
      dispatch(UPDATE_ROW_DATA([]));
      dispatch(SET_BUFFER_INITIAL_DATA([]));
      dispatch(SET_BUFFER_MODIFY_DATA([]));
      dispatch(UPDATE_COLDEFS([]));
      dispatch(REMOVE_ALL_FILTERS());
      dispatch(SET_CCR_INITIAL_DATA([]));
      dispatch(SET_CCR_MODIFY_DATA([]));
      dispatch(SET_POOGI_INITIAL_DATA([]));
      dispatch(SET_POOGI_MODIFY_DATA([]));
      // dispatch(UPDATE_ACTIVE_MASTER([]))

      dispatch(ADD_FILTER());
      dispatch(FILL_MASTERS([]));
      dispatch(TOGGLE_SELECT_MASTER_SCREEN(true));

      dispatch(TOGGLE_UPLOAD_MODAL(true));
    }

    return (
        <Container style={{padding: '20px'}}>
            <PanelGridWrapper>
                <PanelGrid>
                    <IconCard iconOnMouseOut={'/assets/img/VectorFLOW/NMS/edit.svg'} iconOnMouseIn={'/assets/img/VectorFLOW/NMS/edit-hover.svg'} text={'View / Modify Records '}  onClick={()=>{clearVal(),navigate('/mto/master-data-management/control-panel/view-modify')}} themeUi={themeUi}/>
                    <IconCard iconOnMouseOut={'/assets/img/VectorFLOW/NMS/add.svg'} iconOnMouseIn={'/assets/img/VectorFLOW/NMS/add-hover.svg'} text={'Add Records '} onClick={()=>{clearVal(),navigate('/mto/master-data-management/control-panel/add')}} themeUi={themeUi}/>
                </PanelGrid>
            </PanelGridWrapper>
        </Container>
    )
}

export default MTOControlPanel