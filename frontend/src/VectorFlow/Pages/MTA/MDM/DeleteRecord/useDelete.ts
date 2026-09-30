import { useSelector,useDispatch } from 'react-redux'
import { useEffect,useState } from 'react';
import { RootState } from '../../../../../redux/store/store';
import { MDMMasterState,Field } from '../../../../../VectorFlow/types/MDM';
import { UPDATE_ACTIVE_MASTER,RESET_STATE, REMOVE_MASTER, ADD_MASTER,SET_RECORD_COUNT,TOGGLE_SELECT_MASTER_SCREEN,UPDATE_PROGRESS_STATE,UPDATE_COLDEFS,FILL_MASTERS, TOGGLE_UPLOAD_MODAL, UPDATE_ROW_DATA, SYNC_ACTIVE_MASTER_TO_MASTER, REMOVE_COLDEFS,ADD_COLDEFS,SET_DRAFT_ID } from '../../../../../redux/actions/MDM';
import { useNavigate } from "react-router";
import { ColDef } from 'ag-grid-enterprise';
import { useDeleteMasterData ,useDeleteTask,useDeleteDraft,useDeleteMasterDataRetail} from '../../../../..//VectorFlow/Services/MTA/MDM';
import {createErrorRowData } from '../../../../../helpers/utils';

import _ from 'lodash';
import { notifyError,notifyLoader,notifySuccess } from '../../../../../helpers/notify';
import { toast } from 'react-toastify';

const useDelete=()=>{
    const allMasters = useSelector((state:RootState)=>state.mdm.allMasters); 
    const activeMaster = useSelector((state:RootState)=>state.mdm.activeMaster)
    const selectedMasters = useSelector((state:RootState)=>state.mdm.masters)
    const options = useSelector((state:RootState)=>state.mdm.options)
    const selectedOptions = useSelector((state:RootState)=>state.mdm.selectedOptions)
    const chunkSize = useSelector((state:RootState)=>state.mdm.chunkSize);
    const draftID = useSelector((state:RootState) => state.mdm.draftId);
    const dispatch = useDispatch();
    const navigate = useNavigate();

    const {mutateAsync:deleteMasterData} = useDeleteMasterData()

    const {mutateAsync:deleteMasterDataRetail} = useDeleteMasterDataRetail()

    const {mutateAsync:deleteTask} = useDeleteTask();

    const {mutateAsync:deleteDraft} = useDeleteDraft()


    const [TASK_ID,setTaskId] = useState<string>();
    const [conflictCount,setConflictCount] = useState<number>(0);
    const [errorCount,setErrorCount] = useState<number>(0);
    const [errorData,setErrorData] = useState<Array<any>>([]);
    const [isSubmitDisabled,setIsSubmitDisabled] = useState(false);

    useEffect(()=>{
        if(activeMaster.progress === 'deleteOnline'){
            if(activeMaster.colDefs[0].colId!=='checkbox'){
              const updatedColdefs:ColDef[] = [{
                field:'checkbox',
                colId:'checkbox',
                headerName:'',
                checkboxSelection:true,
                headerCheckboxSelection:true,
                headerCheckboxSelectionCurrentPageOnly:true,
                width:40
            },...activeMaster.colDefs]
            dispatch(UPDATE_COLDEFS(updatedColdefs))
            }
        }
        if(activeMaster.progress === 'submitted' || activeMaster.progress==='deleteOnlineSubmitted'){
            dispatch(REMOVE_COLDEFS(['checkbox']))
        }
      },[activeMaster.progress]);


      const invalidDataColdefs:ColDef[] = [
        {
          field:'warning',
          colId:'warning',
          headerName:'Warning',
          floatingFilter:false,
          cellRenderer:'warningCell',
          minWidth:200,
          suppressColumnsToolPanel:true,
          wrapText:true,
          autoHeight:true,
        },
        {
          field:'error',
          colId:'error',
          headerName:'Error',
          floatingFilter:false, 
          cellRenderer:'errorCell',
          suppressColumnsToolPanel:true,
          wrapText:true,
          autoHeight:true,
        }
    ];


    const addInvalidDataColDefs = (columnName:string) => {
        dispatch(ADD_COLDEFS({colDefs:[columnName === 'error' ? invalidDataColdefs[1] : invalidDataColdefs[0]]}));
        // dispatch(SYNC_ACTIVE_MASTER_TO_MASTER())
      }

    const handleOnClickMaster=(master:MDMMasterState)=>{

        //For seasonality
        if(master.id==11){
            const doesSeasonalityMasterExist = selectedMasters.find((m:MDMMasterState)=>m.id==11 || m.id==12)
            if(doesSeasonalityMasterExist){
                dispatch(REMOVE_MASTER(doesSeasonalityMasterExist.id))
                return
            }
            return dispatch(ADD_MASTER({...master,name:'Seasonality'}))
        }
        

        //for PIPO
        if(master.id==7){
            const doesPIPOMasterExist = selectedMasters.find((m:MDMMasterState)=>m.id==7 || m.id==8 || m.id==9)
            if(doesPIPOMasterExist){
                dispatch(REMOVE_MASTER(doesPIPOMasterExist.id))
                return
            }
            return dispatch(ADD_MASTER({...master,name:'Phase In Phase Out'}))
        }

        if(selectedMasters.find((m:MDMMasterState)=>m.id===master.id)){
            dispatch(REMOVE_MASTER(master.id))
            return
        }        
        dispatch(ADD_MASTER(master))
       
    }

    function updateUrlIsModalOpen() {

      const currentUrl = window.location.href;
      

      const hasParameter = currentUrl.includes("isModalOpen=true");

      if (!hasParameter) {

          const [baseUrl, queryString] = currentUrl.split("?");
          

          const newQueryString = queryString ? `${queryString}&isModalOpen=true` : "isModalOpen=true";
          const newUrl = `${baseUrl}?${newQueryString}`;
          

          window.history.replaceState(null,'', newUrl);
      }
  }

    const handleSubmitSelectMaster = ()=>{
      updateUrlIsModalOpen();
        // dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
        // dispatch(UPDATE_ACTIVE_MASTER(0));
        const firstDefaultIndex = selectedMasters.findIndex(
          (item) => item.progress !== 'submitted'
        );
        if (firstDefaultIndex !== -1) {
          dispatch(UPDATE_ACTIVE_MASTER(firstDefaultIndex));
        }
        dispatch(TOGGLE_SELECT_MASTER_SCREEN(false))
    }
    


    const handleRadioButton = (masterFileId:number)=>{
        if(masterFileId==activeMaster.id){
            return
        }
        const isSeasonality = masterFileId==11 || masterFileId==12
        const doesMasterExist = allMasters.find((m:MDMMasterState)=>m.id==masterFileId)
        if(doesMasterExist){
            const newSelectedMasters = selectedMasters.map((master:MDMMasterState)=>{
                if(master.id==activeMaster.id){
                    return {...doesMasterExist,name:isSeasonality?"Seasonality":"Phase In Phase Out"}
                }
                return master
            })
            dispatch(FILL_MASTERS(newSelectedMasters))
            dispatch(UPDATE_ACTIVE_MASTER({...doesMasterExist,name:isSeasonality?"Seasonality":"Phase In Phase Out"}))
        }
        
    }

    const onDeleteOnline = ()=>{
        dispatch(UPDATE_PROGRESS_STATE('deleteOnline'))
      }

    const onDeleteData = ()=>{
        dispatch(TOGGLE_UPLOAD_MODAL(true))
    }

    const onDeleteOnlineReset = ()=>{
        const currentMasterData = selectedMasters.find((master:MDMMasterState)=>master.id === activeMaster.id)
        if(currentMasterData) dispatch(UPDATE_ROW_DATA(currentMasterData.rowData))
        dispatch(UPDATE_PROGRESS_STATE('deleteOnline'))
    }
    
    const onDeleteOnlineSubmit = ()=>{
        dispatch(UPDATE_PROGRESS_STATE('deleteOnlineSubmitted'))
    }


    const onCancel=()=>{
        dispatch(RESET_STATE());
        navigate('/mta/master-data-management/control-panel');
    }

    const postMasterDataChunks = async (rowData:any,isOverWrite?:boolean) => { 

        const columnsToOmit = activeMaster.fields.filter((field:Field)=>!field.isDownload).map((field:Field)=>field.key) 
        rowData = rowData.map((row:any)=>_.omit(row,'error','warning','users',columnsToOmit));

       // Convert To String
       rowData = rowData.map((row:any)=>{
        const tempRow:any = {};
        Object.keys(row).forEach((key:string)=>{
          tempRow[key] = row[key].toString();
        })
        return tempRow;
      });

      const deletableKeys = activeMaster.fields.filter(field => field.isDelete === true).map(field => field.key)
      rowData = rowData.map((obj: any) => {
        return Object.keys(obj).reduce((acc: any, key) => {
          if (deletableKeys.includes(key)) {
            acc[key] = obj[key];
          }
          return acc;
        }, {});
      })


        let taskId:any   = '';
        let toastId:any = '';
        let conflictCount = 0;
        let errorCount = 0;
        const conflictData:any = [];
        const errorData:any = [];
        try {
          let submitProgress = 0;
          const payload:any = {
            id:activeMaster.id,
            action:"",
            TaskId:'',
            IsOverWrite:true,
            data:[],
            uiconfig:activeMaster.fields
          }

          toastId = notifyLoader(`Submitting Data ${submitProgress}/${activeMaster.rowData.length}`);
        
          for(let i=0; i < rowData.length; i+=chunkSize){
          
              if(i+chunkSize < rowData.length){
                payload.data = rowData.slice(i,i+chunkSize);  
                toast.update(toastId,{render:`Submitting Data ${i+chunkSize}/${rowData.length}`})
                submitProgress+=chunkSize;
              }
              else{
                payload.data = rowData.slice(i)
                toast.update(toastId,{render:`Submitting Data ${rowData.length}/${rowData.length}`})
              }
              let data:any;
              if(activeMaster.id > 14) {
                data = await deleteMasterDataRetail(payload);
              }
              else{
                data = await deleteMasterData(payload);
                if (data.status !== 200) {
                  throw new Error(`Request failed with status`);
               }
              }
              
              if(taskId === '' && i!==0) throw new Error("Something Went Wrong");

              if(TASK_ID === '' || TASK_ID === undefined){
                payload.TaskId = data.data.taskId;
                taskId = data.data.taskId;
              }
              else{
                payload.TaskId = TASK_ID;
                taskId = TASK_ID;
              }

              setTaskId(data.data.taskId);
              
              if(data.data.conflictErrorCount){
                conflictCount += parseInt(data.data.conflictErrorCount,10);
              }
              errorCount += parseInt(data.data.errorCount,10);
              const conflictedRows = data.data.conflictError;
              const errorenousRows = data.data.error;
              if(conflictedRows instanceof Array) {
                conflictedRows.forEach((row:any)=>{
                  const userIndex = conflictData.findIndex((data:any)=>data.user === row.user);
                  if(userIndex >= 0){
                    conflictData[userIndex].conflictdetails = [...conflictData[userIndex].conflictdetails,...row.conflictdetails]
                  }
                  else{
                    conflictData.push({
                      user:row.user,
                      conflictdetails:row.conflictdetails
                    })
                  }
                })
              }
              if(errorenousRows instanceof Array) {
                errorenousRows.forEach((row:any)=>{
                  const userIndex = errorData.findIndex((data:any)=>data.errorType === row.errorType);
                  if(userIndex >= 0){
                    errorData[userIndex].errorData = [...errorData[userIndex].errorData,...row.errorData]
                  }
                  else{
                    errorData.push({
                      errorType:row.errorType,
                      errorData:row.errorData
                    })
                  }

                })
              }
            }
            toast.dismiss(toastId);
            setConflictCount(conflictCount);
            setErrorCount(errorCount);
            setErrorData(errorData)
            return {isDisaster:false,errorCount,errorData,conflictCount,conflictData} 
            
          }
         catch (error) {
          notifyError("Something Went Wrong");
          if(taskId.length > 0){
            await deleteTask(taskId);
          }
          toast.dismiss(toastId)
          return {isDisaster:true,errorCount,errorData,conflictCount,conflictData,} 
        }
      }

      const onSubmit = async(ref:any,isOverWrite?:boolean) => {
       try{
        
        if(activeMaster.rowData.length === 0){
          notifyError("No Data to Submit")
          return
        }

        if(ref.current.api.getSelectedRows().length===0 && activeMaster.progress==='deleteOnline'){
          return notifyError("Select rows to delete")
        }

        

        if(isSubmitDisabled) return;
        dispatch(REMOVE_COLDEFS(['checkbox']));

        setIsSubmitDisabled(true)
 
        dispatch(SYNC_ACTIVE_MASTER_TO_MASTER())
     
        
        //let result;
 
        if(activeMaster.progress === 'deleteOnline'){
          const selectedRows = ref.current.api.getSelectedRows()
          // if(selectedRows.length===0) return notifyError("Select rows to delete")
          dispatch(UPDATE_ROW_DATA(selectedRows))
            const {isDisaster,errorCount:localErrorCount,errorData:localErrorData} = await postMasterDataChunks(selectedRows,isOverWrite);
            if(isDisaster)return
            //result = !isConflicts
              if(localErrorCount>0 || errorCount>0){
                let errorRowData
                if(localErrorCount>0){
                  errorRowData = createErrorRowData(localErrorData,activeMaster.id)
                }
                else{
                  errorRowData = createErrorRowData(errorData,activeMaster.id)
                }
                if(!activeMaster.colDefs.find((c:ColDef)=>c.colId==='error')){
                  addInvalidDataColDefs('error')
                }
                dispatch(UPDATE_ROW_DATA(errorRowData))
                dispatch(SET_RECORD_COUNT(errorRowData.length))
              }
              if(draftID.length > 0){
                await deleteDraft(draftID);
                dispatch(SET_DRAFT_ID(''));
              }
              dispatch(UPDATE_PROGRESS_STATE('deleteOnlineSubmitted'));
              dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
              notifySuccess(`Deletions Submitted Successfully`);
          }
         else{
            const {isDisaster,errorCount:localErrorCount,errorData:localErrorData} = await postMasterDataChunks(activeMaster.rowData,isOverWrite);
            if(isDisaster)return
              if(localErrorCount>0 ){
                  let errorRowData: any[] = [];
                if(localErrorCount>0){
                  errorRowData = createErrorRowData(localErrorData,activeMaster.id)
                }
                // else{                  
                //   // errorRowData = createErrorRowData(errorData,activeMaster.id)
                // }
                if(!activeMaster.colDefs.find((c:ColDef)=>c.colId==='error')){
                  addInvalidDataColDefs('error')
                }
                dispatch(UPDATE_ROW_DATA(errorRowData))
                dispatch(SET_RECORD_COUNT(errorRowData.length))
                const totalRecords = activeMaster.rowData.length;
                const submittedRecordsCount = totalRecords - errorRowData.length 

                if(errorRowData.length  === totalRecords){
                  notifyError(`${errorRowData.length} records have error`)
                }
                else if(errorRowData.length  > 0){
                  notifyError(`Submitted ${submittedRecordsCount} records out of ${totalRecords}. ${errorRowData.length} records have error. `)
                }
              }
              if(localErrorCount === 0)
              {
                notifySuccess(`Deletions Submitted Successfully`);
              }
              dispatch(UPDATE_PROGRESS_STATE('submitted'));
              
              dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());          
              if(draftID.length > 0){
                await deleteDraft(draftID);
                dispatch(SET_DRAFT_ID(''));
              }
              if(activeMaster.rowData.length === 0) 
              {
                  dispatch(UPDATE_PROGRESS_STATE('submitted')); 
                  dispatch(REMOVE_COLDEFS(['error','warning']));
              }
            
         }
        }catch(err){
          notifyError("Something went wrong")
        }finally{
         setIsSubmitDisabled(false)
        }
      }

      const showMasterGroup = (currMasterGroup:{name:string,masters:Array<any>})=>{
        if(selectedOptions.length===0)return true
        let shouldShow = false
        currMasterGroup.masters.forEach((m:any)=>{
          const currMaster = allMasters.find((tempMaster)=>tempMaster.id===m)
          if(currMaster){
            currMaster.fields.map((f)=>{
              selectedOptions.forEach((so)=>{
                if(so.value===f.key){
                  shouldShow= true
                }
              })
            })
          }
        })
        return shouldShow
      }

      const showMaster = (currMaster:MDMMasterState)=>{
        if(selectedOptions.length===0)return true
        let shouldShow = false
       
        currMaster.fields.map((f)=>{
          selectedOptions.forEach((so)=>{
            if(so.value===f.key){
              shouldShow= true
            }
          })
        })
        return shouldShow
      }


    return {
        allMasters,
        selectedMasters,
        conflictCount,
        errorCount,
        options,
        selectedOptions,
        onCancel,
        onDeleteOnline,
        onDeleteData,
        onSubmit,
        onDeleteOnlineSubmit,
        onDeleteOnlineReset,
        handleOnClickMaster,
        handleRadioButton,
        handleSubmitSelectMaster,
        showMaster,
        showMasterGroup,
        isSubmitDisabled
    }
}

export default useDelete