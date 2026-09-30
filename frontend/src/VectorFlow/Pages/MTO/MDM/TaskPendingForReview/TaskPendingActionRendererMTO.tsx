import { ICellRendererParams } from "ag-grid-enterprise"
import { ActionRendererWrapper,ActionButtonWrapper } from "./styles"
import { useDispatch, useSelector } from "react-redux"
import _ from "lodash"
import { SET_TASK_PENDING_ROW_DATA} from "../../../../../redux/actions/MTO"


interface TaskPendingActionRendererProps extends ICellRendererParams{
    onApprove:()=>void
    onReject:(id:string)=>void
}

const TaskPendingActionRendererMTO = (props:TaskPendingActionRendererProps| any)=>{

    const dispatch = useDispatch();

    const detailTableRowData = useSelector((state: any)=> state.mto.taskPendingRowData)

    const onClick = (status:string)=>{
        if(status==='Approved'){
            const newData = _.cloneDeep(detailTableRowData);
            newData[props.node.rowIndex].appStatus = true;
            newData[props.node.rowIndex].ia = true;
            
            dispatch(SET_TASK_PENDING_ROW_DATA(newData));
        }
        else{
            const newData = _.cloneDeep(detailTableRowData);
            newData[props.node.rowIndex].appStatus = false;
            newData[props.node.rowIndex].ia = false;
            dispatch(SET_TASK_PENDING_ROW_DATA(newData));
        }
    }

    return (
        <ActionRendererWrapper>
          <ActionButtonWrapper 
            src={
              detailTableRowData[props.node.rowIndex]?.appStatus===true
                ? "/assets/img/VectorFLOW/NMS/task-pending-approve.svg"
                : "/assets/img/VectorFLOW/NMS/task-pending-approve-grey.svg"
            } 
            height={16} 
            width={16} 
            onClick={() => onClick('Approved')} 
          />
          <ActionButtonWrapper 
            src={
              detailTableRowData[props.node.rowIndex]?.appStatus===true
                ? "/assets/img/VectorFLOW/NMS/task-pending-reject-grey.svg"
                : "/assets/img/VectorFLOW/NMS/task-pending-reject.svg"
            } 
            height={16} 
            width={16} 
            onClick={() => onClick('Rejected')} 
          />
        </ActionRendererWrapper>
      );
      
    
   
}

export default TaskPendingActionRendererMTO
