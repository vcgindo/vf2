import { ColDef, ColGroupDef } from "ag-grid-enterprise"
import { useEffect, useRef, useState } from "react"
import { useApproveTask, useGetMasterUIConfiguration, useGetPendingTasks, useGetTaskCount, useGetTaskDetails } from "../../../../../VectorFlow/Services/MTA/MDM"

import { createTaskPendingSubmitPayload, getActionName, getExistingColumnFields, getExistingColumns, mapMasterToColumnGroupDefs, mapNewAndOldMasterRowDataToCustomRowData, mapPendingTaskToColumnDefs } from "../../../../../helpers/utils"
import { GridRef, Master, TaskDataType } from "../../../../../VectorFlow/types/MDM"
import TaskPendingLinkCellRenderer from "./TaskPendingLinkCellRenderer"
import { useSelector, useDispatch } from "react-redux"
import type { RootState } from '../../../../../redux/store/store';
import { toast } from 'react-toastify';
import { notifyLoader,notifyError,notifySuccess } from "../../../../../helpers/notify";
import { SET_RECORD_COUNT } from "../../../../../redux/actions/MDM";
import { useUserData } from "../../../../../context"

const useTaskPendingForReview = ()=>{
    const ref = useRef<GridRef>()
    const dispatch = useDispatch();

    const {user} = useUserData()

    const themeUi = user.user.theme_ui

    const [taskActionype,setTaskActionType] = useState<number>()
    const [isViewTableOpen,setIsViewTableOpen] = useState(true)
    const [viewTableColDefs,setViewTableColDefs] = useState<ColDef[] | ColGroupDef[]>()
    const [detailTableColDefs,setDetailTableColDefs] = useState<ColDef[] | ColGroupDef[]>()
    const [detailTableRowData,setDetailTableRowData] = useState<any[]>([])
    // const [recordCount,setRecordCount] = useState<number>(0)
    const [selectedRows,setSelectedRows] = useState<number>(0)
    const [currentPage,setCurrentPage] = useState<number>(1)
    const [showApproveAllModal,toggleApproveAllModal] = useState<boolean>(false);
    const [showRejectAllModal,toggleRejectAllModal] = useState<boolean>(false);
    const [selectionType,setSelectionType] = useState<string>('');

    const [currMasterId,setCurrMasterId] = useState<number>(0)

    const recordCount = useSelector((state:RootState) => state.mdm.recordCount)
    const rowsPerPage = 50;

    const {data,isLoading,refetch} = useGetPendingTasks()

    const {mutateAsync:getTaskDetails,isLoading:isViewTableLoading} = useGetTaskDetails()

    const {mutateAsync:getMasterUIConfiguration,isError:isMasterUiConfigurationLoading} = useGetMasterUIConfiguration();

    const {mutateAsync:getTaskCount} = useGetTaskCount();

    const {mutateAsync:approveTask } = useApproveTask();

    const chunkSize = useSelector((state:RootState) => state.mdm.chunkSize) 

    const showLoader = isLoading || isMasterUiConfigurationLoading || isViewTableLoading;

    const [actionStatus,setActionStatus] = useState<string>('');

    const [TASK_ID,setTaskId] = useState<string>('')

    const [noDataMessage, setNoDataMessage] = useState<string>('');
    const [colGenArgs, setColGenArgs] = useState<any>(null);
    const [isDisabled, setIsDisabled] = useState<boolean>(false);

    useEffect(() => {
        if (!isViewTableOpen && ref.current?.api && detailTableRowData?.length > 0) {
        let rejectedCount = 0;
        ref.current.api.forEachNode((rowNode) => {
            if (rowNode.data.status === "Rejected") {
                rowNode.setSelected(true)
                rejectedCount++;
            }
        });
        const allRowsAreRejected = rejectedCount === detailTableRowData.length;
        setIsDisabled(allRowsAreRejected);
    }
}, [detailTableRowData, isViewTableOpen]);

useEffect(() => {
    if (colGenArgs) {
        setDetailTableColDefs(
            mapMasterToColumnGroupDefs(
                colGenArgs.existingColumnFields,
                colGenArgs.currentTaskMasterId,
                themeUi,
                colGenArgs.taskActionTypeValue,
                toggleApproveAllModal,
                toggleRejectAllModal,
                actionStatus,
                isDisabled
            )
        );
    }
}, [isDisabled, colGenArgs]); 

    const resetState = ()=>{
        setDetailTableColDefs([])
        setDetailTableRowData([])
        setTaskActionType(0)
        dispatch(SET_RECORD_COUNT(0))
        setSelectedRows(0)
    }

    const handleOnClick = async(taskData:TaskDataType)=>{
        let toastId;
        try {
            resetState()
            
            setTaskId(taskData.TaskID)
            
            setTaskActionType(taskData.Actiontype)
            
            const tempToastId = notifyLoader('Loading Data')
            const res:any = await getTaskCount(taskData.TaskID);

            const taskCount = JSON.parse(res.data.recordCount)[0].recordcount;
            dispatch(SET_RECORD_COUNT(taskCount));
         
            let taskDataStore:any = [];
            const payload = {
                taskId:taskData.TaskID,
                paginationParameter:{
                    pageNumber:1,
                    recordsPerPage:chunkSize
                }
            }
            toast.dismiss(tempToastId)
            toastId = notifyLoader(`Downloading Data 0 / ${taskCount}`)

            if(taskCount <= chunkSize){
                const result = await getTaskDetails(payload);
                taskDataStore = result.data.data;
            }
            else{
                const numberOfPages = Math.ceil(taskCount/chunkSize);
                for(let i=1; i<=numberOfPages; i++){
                    payload.paginationParameter.pageNumber = i;
                    const result = await getTaskDetails(payload)
                    if(i===1){
                        taskDataStore.push(...result.data.data);
                    }
                    console.log(result.data.data)
                    if(i!==1)  taskDataStore[0].data.push(...result.data.data[0].data);
                    if(i===numberOfPages) toast.update(toastId,{render:`Downloading Data ${taskCount} / ${taskCount}`})
                    else toast.update(toastId,{render:`Downloading Data ${i*chunkSize} / ${taskCount}`})
                }
            }
            // const response = await getTaskDetails(payload)
            toast.dismiss(toastId);
            
            if (taskDataStore[0].data?.length != undefined) {
                // Proceed with setting columns and row data
                const currentTaskMaster = taskDataStore[0];
                const currentTaskMasterId: number = currentTaskMaster.MasterId;
                setCurrMasterId(currentTaskMasterId);

                // ...existing code for processing data
                setNoDataMessage(''); // Clear message if we have data
                
                    const uiConfigurationResponse = await getMasterUIConfiguration(getActionName(taskData.Actiontype).value)
                
                    const masters:Master[] = uiConfigurationResponse.data.data
                    const currentMasterFields = masters.find((master:Master)=>master.id==currentTaskMasterId)?.fields
                    if(currentMasterFields){
                        // console.log(currentTaskMaster.data[0].new)
                        const existingColumns = getExistingColumns(
                            currentTaskMaster.data?
                            (taskData.Actiontype === 2 && currentTaskMasterId !== 6 && currentTaskMasterId !== 10) || (currentTaskMasterId === 13)
                            ? JSON.parse(currentTaskMaster?.data[0].new)
                            : currentTaskMaster?.data[0]:[]
                        );
                                       
                        let existingColumnFields = getExistingColumnFields(existingColumns,currentMasterFields);
                        if(taskData.Actiontype === 3){
                            existingColumnFields = existingColumnFields.filter(field =>
                                field?.isDelete || field?.key === 'sd' || field?.key === 'wd'
                              );
                        }
                        // setDetailTableColDefs(mapMasterToColumnGroupDefs(existingColumnFields,currentTaskMasterId,themeUi,getActionName(taskData.Actiontype).value,toggleApproveAllModal,toggleRejectAllModal,actionStatus,isDisabled))
                        setColGenArgs({
                            existingColumnFields: existingColumnFields,
                            currentTaskMasterId: currentTaskMasterId,
                            taskActionTypeValue: getActionName(taskData.Actiontype).value
                        });
                        setDetailTableRowData(mapNewAndOldMasterRowDataToCustomRowData(currentTaskMaster.data,existingColumnFields,getActionName(taskData.Actiontype).value,currentTaskMasterId))
                        // dispatch(SET_RECORD_COUNT(currentTaskMaster.data.length));
                    }
            } else {
                // No data case
                setNoDataMessage('No Data To Approve.');
            }
            

            notifySuccess("Task Details Fetched Successfully");
            setIsViewTableOpen(false)
            
        } catch (error) {
            toast.dismiss();
            console.log(error)
            notifyError("Something Went Wrong");
            
        }
        
    }

    const handleChangePage = async (pageNo:any) => {
        setCurrentPage(pageNo);
        ref.current?.api.paginationGoToPage(pageNo);
      }

    const onCancel = ()=>setIsViewTableOpen(true)

    const onTaskSubmit = async () => {  
        
       
        let toastId;
        const updatedRowData = createTaskPendingSubmitPayload(detailTableRowData,taskActionype || 0,currMasterId)
        console.log(updatedRowData)
        
        try {
            const noActionPerformed = updatedRowData.find((row:any)=>row.status === '');

            if(noActionPerformed){
                notifyError("Please Update the Status for all Rows before submitting")
                return
            }
            let submitProgress = 0;
 
            const payload:any =  {
                taskId:TASK_ID,
                recordCount:recordCount,
                data:[]
            }

            toastId = notifyLoader(`Submitting Data ${submitProgress}/${updatedRowData.length}`);
    
            for(let i=0; i < recordCount; i+=chunkSize){
                if(i+chunkSize < updatedRowData.length){
                    payload.data = updatedRowData.slice(i,i+chunkSize);
                    toast.update(toastId,{render:`Submitting Data ${i+chunkSize}/${updatedRowData.length}`})
                    submitProgress+=chunkSize;
                }
                else{
                    payload.data = updatedRowData.slice(i)
                    toast.update(toastId,{render:`Submitting Data ${updatedRowData.length}/${updatedRowData.length}`})
                }
                
                await approveTask(payload);
            }
            toast.dismiss(toastId);
            setIsViewTableOpen(true);
            setDetailTableColDefs([]);
            setDetailTableRowData([]);
            setCurrentPage(1);
            setSelectedRows(0);
            setSelectionType('');
            refetch()
            notifySuccess('Data submitted successfully and Task status updated');

            
        } catch (error) {
            toast.dismiss();
            notifyError('Something Went Wrong');
        }
       
    }

    const onSelectionTypeSuccess = (status:string,) => {
        const pageSize:any = ref.current?.api.paginationGetPageSize()
        const currentPage:any = ref.current?.api.paginationGetCurrentPage()
        const filteredData:any = []
        ref.current?.api.forEachNodeAfterFilter((n) => {
            filteredData.push(n.id)
        })
        const startIndex = currentPage * pageSize
        const endIndex = startIndex + pageSize

        const pageData = filteredData.slice(startIndex, endIndex);
        
    
        switch (selectionType){
            case 'All':
                 ref.current?.api.forEachNode((rowNode)=>{
                    if(rowNode.data.isModified){
                        rowNode.setDataValue('status',status)
                        rowNode.setSelected(true)
                    }
                    if(!rowNode.data.isModified && taskActionype===2 && status==="Rejected"){
                        rowNode.setDataValue('status',status)
                        rowNode.setSelected(true)
                    }
                    else if(taskActionype!==2 || currMasterId===6){
                        rowNode.setDataValue('status',status)
                        rowNode.setSelected(true)
                    }
                })
                setActionStatus(status);
                break;
            case 'Current':
                ref.current?.api.forEachNode((rowNode)=>{
                    if(pageData.includes(rowNode.id) && rowNode.data.isModified){
                        rowNode.setDataValue('status',status)
                        rowNode.setSelected(true)
                        
                    }
                    if(pageData.includes(rowNode.id) && !rowNode.data.isModified && taskActionype===2 && status==="Rejected"){
                        rowNode.setDataValue('status',status)
                        rowNode.setSelected(true)
                    }
                    else if(pageData.includes(rowNode.id) && (taskActionype!==2 || currMasterId===6)){
                        rowNode.setDataValue('status',status)
                        rowNode.setSelected(true)
                    }
                    
                })
                break;
            default:
                return;

        }
  
        if(status === 'Approved'){
            toggleApproveAllModal(false);
        }
        else{
            toggleRejectAllModal(false);
        }
    }

    useEffect(()=>{
        setViewTableColDefs(mapPendingTaskToColumnDefs([
            {
                field:"SrNo",
                colId:"SrNo",
                headerName:"Sr No.",
            },
            {
                field:"PendingSince",
                colId:"PendingSince",
                headerName:"Pending Since",
            },
            {
                field:"ageing",
                colId:"ageing",
                headerName:"Ageing",
            },
            {
                field:"TaskName",
                colId:"TaskName",
                headerName:"Task Name",
                cellRenderer:TaskPendingLinkCellRenderer,
                cellRendererParams:{
                    onClick:handleOnClick
                }
            },
            {
                field:"RequesterName",
                colId:"RequesterName",
                headerName:"Requester",                  
            }
        ]))
        
    },[])
    return{
        ref,
        isViewTableOpen,
        viewTableColDefs,
        detailTableColDefs,
        viewTableRowData : data?.data.data,
        detailTableRowData,
        showLoader,
        recordCount,
        selectedRows,
        setSelectedRows,
        currentPage,
        rowsPerPage,
        handleChangePage,
        handleOnClick,
        onCancel,
        onTaskSubmit,
        showApproveAllModal,
        toggleApproveAllModal,
        showRejectAllModal,
        toggleRejectAllModal,
        onSelectionTypeSuccess,
        setSelectionType,
        noDataMessage
    }
}

export default useTaskPendingForReview



