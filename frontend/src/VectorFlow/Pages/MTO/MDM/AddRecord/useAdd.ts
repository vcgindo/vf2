import { useSelector,useDispatch } from 'react-redux'
import { RootState } from '../../../../../redux/store/store';
import { MDMMasterState } from '../../../../../VectorFlow/types/MDM';
import { REMOVE_MASTER,UPDATE_ACTIVE_MASTER,ADD_COLDEFS, UPDATE_PROGRESS_STATE, FILL_MASTERS, TOGGLE_UPLOAD_MODAL, TOGGLE_SELECT_MASTER_SCREEN ,SYNC_ACTIVE_MASTER_TO_MASTER,REMOVE_COLDEFS,UPDATE_ROW_DATA,SET_RECORD_COUNT, RESET_STATE} from '../../../../../redux/actions/MDM';
import { useNavigate } from "react-router";
import { useEffect, useState } from 'react';

import { notifyError,notifyLoader,notifySuccess } from '../../../../../helpers/notify';
import _ from 'lodash';
import { toast } from 'react-toastify';
import { useAddMasterData,useDeleteTask,useDeleteDraft,useAddMasterDataRetail, useGetBufferTypeMaster } from '../../../../../VectorFlow/Services/MTA/MDM';
import { createErrorRowData} from '../../../../../helpers/utils'
import { ColDef } from 'ag-grid-enterprise';
import { RESET_MTO_STATE } from '../../../../../redux/actions/MTO';


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
    const [errorCount,setErrorCount] = useState<number>(0);
    const [errorData,setErrorData] = useState<Array<any>>([]);
    const [isSubmitDisabled,setIsSubmitDisabled] = useState(false);
    const bufferInitialData = useSelector((state: any)=> state.mto.bufferInitialData);
    const ccrInitialData = useSelector((state: any)=> state.mto.ccrInitialData);

    const {mutateAsync: getBufferTypeMaster} = useGetBufferTypeMaster();

    const [bufferTypeData, setBufferTypeData] = useState<any>();

    const getBufferTypeMasterData = async()=>{
      try{
        const BufferTypeMaster = await getBufferTypeMaster();
        setBufferTypeData(BufferTypeMaster?.data?.data);
      }
      catch(e){
        console.error(e)
      }
    }

    useEffect(()=>{
      if(activeMaster.id===501){
        getBufferTypeMasterData();
      }
    },[activeMaster.id])

    const invalidDataColdefs:ColDef[] = [
        {
          field:'warning',
          colId:'warning',
          headerName:'Warning',
          floatingFilter:false,
          cellRenderer:'warningCell',
          minWidth:200,
          suppressColumnsToolPanel:true
        },
        {
          field:'error',
          colId:'error',
          headerName:'Error',
          floatingFilter:false, 
          cellRenderer:'errorCell',
          suppressColumnsToolPanel:true,
          minWidth: 300
        }
    ];


    const addInvalidDataColDefs = (columnName:string) => {
        if(activeMaster.isMTO){
          dispatch(ADD_COLDEFS({colDefs: [invalidDataColdefs[0]]}));
        }
        else{
          dispatch(ADD_COLDEFS({colDefs:[columnName === 'error' ? invalidDataColdefs[1] : invalidDataColdefs[0]]}));
          // dispatch(SYNC_ACTIVE_MASTER_TO_MASTER())
        }
      }

    const onCancel=()=>{
        dispatch(RESET_STATE());
        dispatch(RESET_MTO_STATE());
        navigate('/mto/master-data-management/control-panel');
    }

    const handleOnClickMaster=(master:MDMMasterState)=>{


        if(selectedMasters.find((m:MDMMasterState)=>m.id===master.id)){
            dispatch(REMOVE_MASTER(master.id))
            return
        }        
        dispatch(FILL_MASTERS([master]))
       
    }

    const handleSubmitSelectMaster = ()=>{
        dispatch(UPDATE_ACTIVE_MASTER(0));
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

            dispatch(UPDATE_ACTIVE_MASTER(nextMasterIndex))
            dispatch(TOGGLE_UPLOAD_MODAL(true))
            return 
        }
        else return notifyError(`Please complete the activity in ${selectedMasters[nextMasterIndex].name}`);  
  
        
        
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
            IsOverWrite:isOverWrite===true?true:false,
            data:[]
          }

          toastId = notifyLoader(`Submitting Data ${submitProgress}/${activeMaster.rowData.length}`);
        
          for(let i=0; i < rowData.length; i+=chunkSize){
          
              if(i+chunkSize < rowData.length){
                payload.data = activeMaster.rowData.slice(i,i+chunkSize);
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

              if(TASK_ID === ''){
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
        if(isSubmitDisabled) return;
 
        if(activeMaster.rowData.length === 0) return notifyError("No Data to Submit")

        setIsSubmitDisabled(true)
 
        dispatch(SYNC_ACTIVE_MASTER_TO_MASTER())
     
        //let result;
 
        
          const {isDisaster,errorCount:localErrorCount,errorData:localErrorData} = await postMasterDataChunks(activeMaster.rowData,isOverWrite);
          let errorRowData = [];

          if(isDisaster)return
            if(localErrorCount>0 || errorCount>0){
              if(localErrorCount > 0){
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
            dispatch(REMOVE_COLDEFS(['checkbox']));


            if(errorRowData.length > 0) notifyError("Addition Unsuccessfull")
            else notifySuccess(`Additions Submitted Successfully`);
            dispatch(UPDATE_PROGRESS_STATE('submitted'));
            dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
            if(draftID.length > 0){
              await deleteDraft(draftID);
            }
            setIsSubmitDisabled(false)


          
      }

      // TODO : mto 
      const getErrorForMaster = (ele: any, index: any, tempData:any) => {
        if (activeMaster.id === 501) {
          // Check if the Buffer Type or Buffer Size is missing
          if (!ele.bt || !ele.bsz) {
            return { error: "Enter Buffer Type and Buffer Size", warning: "" };
          }

          if(Number(ele.bsz)<=0){
            return { error: "Buffer size must be greater than 0", warning: ""};
          }
          if(Number(ele.bsz)>365){
            return {error: "Buffer size cannot exceed for over a year", warning: ""};
          }
      
          // Check if Buffer Code already exists in the master data
          const isBufferCodeDuplicate = bufferInitialData.some(
            (master: any) => master.bcd === ele.bcd
          );
          const isbufferCodeDuplicateInCurr = activeMaster.rowData.some(
            (row: any, i: any) => i !== index && row.bcd === ele.bcd
          );
          if (isbufferCodeDuplicateInCurr) {
            return { error: "Buffer code must be unique within the current list!", warning: "" };
          }
          if (isBufferCodeDuplicate) {
            return { error: "Buffer code already exists in master", warning: "" };
          }
        const isBufferTypeValid = bufferTypeData?.some((btData:any) => btData.nm === ele.bt);
          if (!isBufferTypeValid) {
            return { error: "Choose a valid buffer type from the drop down", warning: "" };
          }
          // Check if Buffer Size for the Buffer Type already exists in the master data
          const isBufferTypeAndSizeDuplicate = bufferInitialData.some(
            (master: any) => master.bt === ele.bt && master.bsz === ele.bsz
          );
          if (isBufferTypeAndSizeDuplicate) {
            return { error: "Buffer size for the buffer type already exists in master", warning: "" };
          }
      
          // Check if the Buffer Size is unique within the active master row data
          const isBszUnique = tempData.every((row: any, i: any) => {
            // Skip the current index during validation
            if (i === index) return true;
            // Check for duplicate Buffer Type and Buffer Size
            return !(row.bt === ele.bt && row.bsz === ele.bsz);
          });
          if (!isBszUnique) {
            return { error: "Buffer size must be unique for a given buffer type", warning: "" };
          }
        } else if (activeMaster.id === 502) {
      
          if (!ele.cnm || ele.cnm === "") {
            return { error: "CCR name cannot be empty!", warning: "" };
          }
      
          // Check if CCR Capacity Per Day (cpd) is missing or <= 0
          if (!ele.cpd || ele.cpd <= 0) {
            return { error: "CCR Capacity Per Day must be greater than 0!", warning: "" };
          }
      
          // Check if Working Hours Per Day (whpd) is missing or <= 0
          if (!ele.whpd || ele.whpd <= 0) {
            return { error: "Working Hours Per Day must be greater than 0!", warning: "" };
          }
      
          // Check if Scheduling Horizon (sh) is missing
          if (!ele.sh || ele.sh === "") {
            return { error: "Scheduling horizon cannot be empty!", warning: "" };
          }
      
          // Check if Resource Buffer (rb) is within the range [0, 1]
          if (ele.rb === undefined || ele.rb < 0 || ele.rb > 1) {
            return { error: "Resource buffer (rb) must be between 0 and 1!", warning: "" };
          }
      
          // Check if Capacity Workload (cwl) is > 0
          if (!ele.cwl || ele.cwl <= 0) {
            return { error: "Capacity workload (cwl) must be greater than 0!", warning: "" };
          }
      
          // Check if CCR Code is unique within the initial master data
          const isCcrCodeDuplicate = ccrInitialData.some(
            (master: any) => master.ccd === ele.ccd
          );
          
          const isCcrCodeDuplicateInCurr = tempData.some(
            (row: any, i: any) => ((i < index) && (row.ccd === ele.ccd))
          );
          if (isCcrCodeDuplicateInCurr) {
            return { error: "CCR code must be unique!", warning: "" };
          }
          if (isCcrCodeDuplicate) {
            return { error: "CCR code exists in master data!", warning: "" };
          }
        }
        
        // No errors found
        return { error: "", warning: "" };
      };
      
      

      const onDataChange = (data: any)=>{
        const tempRowData:any = [...activeMaster.rowData];
        const finData:any = [];
        tempRowData.forEach((ele:any, index: any)=>{
          const newVal = _.cloneDeep(ele);
          if(index===data.rowIndex){
            newVal[data.column.colId] = data.newValue;
          }
          finData.push(newVal);
        });
        finData.forEach((ele:any, index: any)=>{

          ele.err= getErrorForMaster(ele, index,finData);
        })

        dispatch(UPDATE_ROW_DATA(finData))
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
        errorCount,
        onSubmit,
        handleOnClickMaster,
        handleSubmitSelectMaster,
        handleRadioButton,
        handleTabChange,
        showMasterGroup,
        showMaster,
        options,
        selectedOptions,
        onDataChange
    }
}

export default useAdd