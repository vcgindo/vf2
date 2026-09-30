import { ActionHeaderContent, ActionHeaderWrapper, TaskPendingActionHeaderButton } from "./styles"
import { useUserData } from "../../../../../context";
import { useDispatch, useSelector } from "react-redux";
import { SET_TASK_PENDING_ROW_DATA } from "../../../../../redux/actions/MTO";
import _ from "lodash";

const TaskPendingActionHeader = (props:any)=>{

  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const dispatch = useDispatch();
  const detailTableRowData = useSelector((state: any)=> state.mto.taskPendingRowData)
    const handleChange = (query:string)=>{
      if(query==="Approved"){
        const newRowData = _.cloneDeep([...detailTableRowData]);
        newRowData.forEach((e)=>{
          e.appStatus = true;
          e.ia = true
        })
        dispatch(SET_TASK_PENDING_ROW_DATA(newRowData));
      }
      else{
        const newRowData = _.cloneDeep([...detailTableRowData]);
        newRowData.forEach((e)=>{
          e.appStatus = false;
          e.ia = false
        })
        dispatch(SET_TASK_PENDING_ROW_DATA(newRowData));
      }
      props.api.refreshCells();      
    }

    return( 
        <ActionHeaderWrapper>   
            <ActionHeaderContent>
                <TaskPendingActionHeaderButton themeUi={themeUi}  onClick={()=>handleChange("Approved")} >Approve All</TaskPendingActionHeaderButton>
            </ActionHeaderContent>
            <ActionHeaderContent>
                <TaskPendingActionHeaderButton themeUi={themeUi} onClick={()=>handleChange("Rejected")} >Reject All</TaskPendingActionHeaderButton>
            </ActionHeaderContent> 
        </ActionHeaderWrapper>
    )
}

export default TaskPendingActionHeader
