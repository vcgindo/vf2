import { useSelector,useDispatch } from 'react-redux'
import { RootState } from '../../../../../redux/store/store';
import { MDMMasterState } from '../../../../../VectorFlow/types/MDM';
import { RESET_STATE, REMOVE_MASTER, ADD_MASTER,UPDATE_ACTIVE_MASTER,ADD_COLDEFS, UPDATE_PROGRESS_STATE, FILL_MASTERS,SET_DRAFT_ID, TOGGLE_UPLOAD_MODAL, TOGGLE_SELECT_MASTER_SCREEN ,SYNC_ACTIVE_MASTER_TO_MASTER,REMOVE_COLDEFS,UPDATE_ROW_DATA,SET_RECORD_COUNT} from '../../../../../redux/actions/MDM';
import { useNavigate } from "react-router";
import { useState } from 'react';

import { notifyError,notifyLoader,notifySuccess } from '../../../../../helpers/notify';
import _ from 'lodash';
import { toast } from 'react-toastify';
import { useAddMasterData,useDeleteTask,useDeleteDraft,useAddMasterDataRetail } from '../../../../../VectorFlow/Services/MTA/MDM';
import { createErrorRowData} from '../../../../../helpers/utils'
import { ColDef } from 'ag-grid-enterprise';


const useAdd=()=>{
    const allMasters = useSelector((state:RootState)=>state.mdm.allMasters); //empty arrya jaha data jaega api se
    const selectedMasters = useSelector((state:RootState)=>state.mdm.masters)
    const activeMaster = useSelector((state:RootState)=>state.mdm.activeMaster)
    const chunkSize = useSelector((state:RootState)=>state.mdm.chunkSize)
    const options = useSelector((state:RootState)=>state.mdm.options)
    const selectedOptions = useSelector((state:RootState)=>state.mdm.selectedOptions)
    const dispatch = useDispatch();
    const navigate = useNavigate();


    const isSelectMasterOpen = useSelector((state:RootState)=>state.mdm.isSelectMasterOpen)
    const draftID = useSelector((state:RootState) => state.mdm.draftId);

    const {mutateAsync:addMaster} = useAddMasterData();

    const {mutateAsync:addMasterRetail} = useAddMasterDataRetail()

    const {mutateAsync:deleteTask} = useDeleteTask();

    const {mutateAsync:deleteDraft} = useDeleteDraft()

    
    const [TASK_ID,setTaskId] = useState<string>();
    const [conflictCount,setConflictCount] = useState<number>(0);
    const [errorCounts,setErrorCount] = useState<number>(0);
    const [errorData,setErrorData] = useState<Array<any>>([]);
    const [isSubmitDisabled,setIsSubmitDisabled] = useState(false);

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

    const onCancel=()=>{
        dispatch(RESET_STATE());
        navigate('/mta/master-data-management/control-panel');
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

    const handleSubmitSelectMaster = ()=>{
      // dispatch(UPDATE_ACTIVE_MASTER(0));
      const firstDefaultIndex = selectedMasters.findIndex(
        (item) => item.progress !== 'submitted'
      );
      
      if (firstDefaultIndex !== -1) {
        dispatch(UPDATE_ACTIVE_MASTER(firstDefaultIndex));
      }
      else{
        dispatch(UPDATE_ACTIVE_MASTER(selectedMasters?.length - 1));
        dispatch(TOGGLE_UPLOAD_MODAL(false))
      }      
      dispatch(TOGGLE_SELECT_MASTER_SCREEN(false))
        if(selectedMasters[0].progress==='default' || selectedMasters[0].progress==='view'){
            if(selectedMasters[0].rowData.length<=0)dispatch(TOGGLE_UPLOAD_MODAL(true))
            dispatch(UPDATE_PROGRESS_STATE('view'))
            return 
        }

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

    const handleTabChange = (currMaster: MDMMasterState) => {
        if(currMaster.progress === 'submitted') return notifyError(`The ${currMaster.name} is already submitted`);

        if(currMaster.id===activeMaster.id)return 
  
        const nextMasterIndex = selectedMasters.findIndex((master:MDMMasterState)=>master.progress !== 'submitted');
  
        if(currMaster.id === selectedMasters[nextMasterIndex].id){
            dispatch(SET_DRAFT_ID(''));
            dispatch(UPDATE_ACTIVE_MASTER(nextMasterIndex))
            dispatch(TOGGLE_UPLOAD_MODAL(true))
            return 
        }
        else return notifyError(`Please complete the activity in ${activeMaster.name}`);  
  
        
        
      }

      const postMasterDataChunks = async (rowData:any,isOverWrite?:boolean) => { 

        rowData = rowData.map((row:any)=>_.omit(row,'error','warning','users'));



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
                data = await addMasterRetail(payload);
              }
              else{
                data = await addMaster(payload);
              }

              if(taskId === '' && i!==0) throw new Error("Something Went Wrong");

              if(TASK_ID === ''  || TASK_ID === undefined){
                payload.TaskId = data.data.taskId;
                taskId = data.data.taskId;
              }
              else{
                payload.TaskId = TASK_ID;
                taskId = TASK_ID;
              }

              setTaskId(data.data.taskId  );
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
          return {isDisaster:true,errorCount,errorData,conflictCount,conflictData} 
        }finally{
          toast.dismiss(toastId)
        }
      }

      const onSubmit = async(isOverWrite?:boolean) => {
        try{
        if(isSubmitDisabled) return;
        if(activeMaster.rowData.length === 0) return notifyError("No Data to Submit")
        dispatch(REMOVE_COLDEFS(['checkbox','warning']));
        setIsSubmitDisabled(true)
 
        dispatch(SYNC_ACTIVE_MASTER_TO_MASTER())
     
        //let result;
          const totalRecords = activeMaster.rowData.length
        
          const {isDisaster,errorCount:localErrorCount,errorData:localErrorData,conflictCount} = await postMasterDataChunks(activeMaster.rowData,isOverWrite);
          let errorRowData:any = [];

          if(isDisaster){
            notifyError("Something went wrong !")
            return
          }

          if (localErrorCount > 0) {
            errorRowData = localErrorData.flatMap((errorObj: any) =>
              errorObj.errorData.map((row: any) => ({
                  ...row,
                  error: errorObj.errorType,
              })),
          );
          
            if (!activeMaster.colDefs.find((c: ColDef) => c.colId === 'error')) {
              addInvalidDataColDefs('error')
            }
            dispatch(UPDATE_ROW_DATA(errorRowData))
            dispatch(SET_RECORD_COUNT(errorRowData.length))
            
          }

          const submittedRecordsCount = totalRecords - errorRowData.length - conflictCount

          if(submittedRecordsCount === totalRecords){
            notifySuccess("Added Successfully")
          }

          else if(errorRowData.length > 0 || conflictCount > 0){

            if(errorRowData.length && conflictCount){
              if(submittedRecordsCount === 0){
                notifyError(`${errorRowData.length} records have error and ${conflictCount} records have conflicts. `)
              }
              else notifyError(`Submitted ${submittedRecordsCount} records out of ${totalRecords}. ${errorRowData.length} records have error and ${conflictCount} records have conflicts. `)
            }

            else if(errorRowData.length){
              notifyError(`Submitted ${submittedRecordsCount} records out of ${totalRecords}. ${errorRowData.length} records have error. `)
            }
            else{
              notifyError(`Submitted ${submittedRecordsCount} records out of ${totalRecords}. ${conflictCount} records have conflicts. `)
            }
          }
          else notifySuccess("Added Successfully")
          dispatch(UPDATE_PROGRESS_STATE('submitted'));
          dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
          if(draftID.length > 0){
            await deleteDraft(draftID);
            dispatch(SET_DRAFT_ID(''));
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
        onCancel,
        selectedMasters,
        activeMaster,
        isSelectMasterOpen,
        conflictCount,
        errorCount:errorCounts,
        onSubmit,
        handleOnClickMaster,
        handleSubmitSelectMaster,
        handleRadioButton,
        handleTabChange,
        showMasterGroup,
        showMaster,
        options,
        selectedOptions,
        isSubmitDisabled
    }
}

export default useAdd