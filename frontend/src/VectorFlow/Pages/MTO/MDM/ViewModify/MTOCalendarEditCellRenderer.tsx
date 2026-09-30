import { useSelector } from "react-redux";
import { RootState } from "../../../../../redux/store/store";


const MTOCalendarEditCellRenderer = (props:any ) => {

  const {handleOpenClick, node, onDeleteUndoHandler, onDeleteHandler, } = props;
  const activeMaster = useSelector(
    (state: RootState) => state.mdm.activeMaster
  );

  return (
    <>
     <div style={{display: 'flex', margin:'4px auto', width: '80px', justifyContent:'center',opacity:node.data.id ? 0.6: 1}}>
        <button onClick={()=>{handleOpenClick(props.node.rowIndex, props.data)}} style={{background: 'transparent'}}>
            <img height={16} width={16} src="/assets/img/VectorFLOW/NMS/edit-draft.svg" />
        </button>
        {node.data.id === true ?

          <button style={{background: 'transparent', color: 'green'}} onClick={() => onDeleteUndoHandler(node.rowIndex, activeMaster.rowData)}>
          <img
            height={18}
            width={18}
            src="/assets/img/delete-undo.svg"
            alt="undo"
            />
          </button>
          :
          <button style={{background: 'transparent', color : 'red'}} onClick={() => onDeleteHandler(node.rowIndex,activeMaster.rowData)}>
            <img height={16} width={16} src="/assets/img/VectorFLOW/NMS/delete-draft.svg" />
          </button>
        }
       
    </div>
    </>
  )
}

export default MTOCalendarEditCellRenderer