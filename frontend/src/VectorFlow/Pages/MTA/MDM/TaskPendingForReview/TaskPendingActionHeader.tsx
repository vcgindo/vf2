import { ActionHeaderContent, ActionHeaderWrapper, TaskPendingActionHeaderButton } from "./styles"
import { useUserData } from "../../../../../context";


const TaskPendingActionHeader = (props:any)=>{

  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;

  // const [actionStatus,setActionStatus] = useState<string>('')

    


    // const onUnCheckAll = ()=>{
    //     props.api.forEachNode((rowNode:any)=>{
    //         rowNode.setDataValue('status','')
    //         rowNode.setSelected(false)
    //     })
    // }

    const handleChange = (unCheckEvent:boolean,query:string)=>{
      // if(!unCheckEvent){
      //   onUnCheckAll()
      // }
      // else {

      // }

      if(query === 'Approved'){
        props.showApproveAllModal(true)
      }
      else{
        props.showRejectAllModal(true)
      }
      
        // if(unCheckEvent){
        //     onUnCheckAll()
        //     setActionStatus('')
        //     return 
        // }
        // setActionStatus(query)
        // props.api.forEachNode((rowNode)=>{
        //     rowNode.setDataValue('status',query)
        //     rowNode.setSelected(true)
        // })
        
    }

    
  // useEffect(() => {
  //   // Check for mismatched statuses and uncheck checkboxes if needed
  //   // const handleStatusMismatch = (query: string) => {
  //   //   props.api.forEachNode((rowNode:any) => {
  //   //     if (rowNode.data.status !== query) {
  //   //       setActionStatus(''); // Uncheck the checkbox
  //   //       return; // No need to continue iterating
  //   //     }
  //   //   });
  //   // };

  //   // handleStatusMismatch('Approved');
  //   // handleStatusMismatch('Rejected');

  //   // const totalRows = props.api.paginationGetRowCount();
  //   // const selectedRows = props.api.getSelectedRows();
  //   // const approvedRows = selectedRows.filter((row:any)=>row.status === 'Approved');
  //   // if(approvedRows.length === totalRows) setActionStatus('Approved');





  // }, [props.api.getSelectedRows()])

  

    return( 
        <ActionHeaderWrapper>   
            <ActionHeaderContent>
                <TaskPendingActionHeaderButton themeUi={themeUi}  onClick={()=>handleChange(props.actionStatus==='Approved',"Approved")} disabled={props.disabled} >Approve All</TaskPendingActionHeaderButton>
            </ActionHeaderContent>
            <ActionHeaderContent>
                <TaskPendingActionHeaderButton themeUi={themeUi} onClick={()=>handleChange(props.actionStatus==='Rejected',"Rejected")} >Reject All</TaskPendingActionHeaderButton>
            </ActionHeaderContent> 
        </ActionHeaderWrapper>
    )
}

export default TaskPendingActionHeader
