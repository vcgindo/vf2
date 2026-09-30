import { useState } from "react"
import { useDispatch,useSelector } from "react-redux"
import { useNavigate } from "react-router"
import {useGetAllDrafts, useDeleteDraft,useGetDraftById,useGetMasterUIConfiguration, useGetDraftCount } from "../../../../../VectorFlow/Services/MTA/MDM"
import { notifyError, notifyPromise, notifySuccess, notifyLoader } from "../../../../../helpers/notify"

import { FILL_MASTERS, SET_DRAFT_ID,TOGGLE_UPLOAD_MODAL, SET_RECORD_COUNT, STORE_ALL_MASTERS, TOGGLE_SELECT_MASTER_SCREEN, UPDATE_ACTIVE_MASTER, UPDATE_DATA_AVAILABILITY_STATUS } from "../../../../../redux/actions/MDM"
import { createMastersStateFromDraftData, getActionName, mapMasterToMasterState } from "../../../../../helpers/utils"
import { MDMMasterState } from "../../../../../VectorFlow/types/MDM"
import type { RootState } from '../../../../../redux/store/store';
import { toast } from 'react-toastify';
import _ from 'lodash';

const useSavedDrafts = ()=>{

    const dispatch = useDispatch()
    const navigate = useNavigate()

    const {mutateAsync:getDraftById} = useGetDraftById()
    const {mutateAsync:getMasterUIConfiguration} = useGetMasterUIConfiguration()
    const {mutateAsync:deleteDraft} = useDeleteDraft()
    const [isDeleteModalOpen,toggleDeleteModal] = useState<boolean>(false)
    const [deleteDraftId,setDeleteDraftId] = useState<string>("");
    const {data,isLoading,refetch} = useGetAllDrafts();
    const {mutateAsync:getDraftCount} = useGetDraftCount();
    const chunkSize = useSelector((state:RootState) => state.mdm.chunkSize)
    const allDrafts = data?.data.data;
  

    const openDeleteModal = (draftId:string)=>{
        setDeleteDraftId(draftId)
        toggleDeleteModal(true)
    }

    const closeDeleteModal =()=>toggleDeleteModal(false)

    const onEditDraft = async(draftDetails:any)=>{
       let toastId;

       try{
        
        const res:any = await getDraftCount(draftDetails.DraftId);
        const draftCount = JSON.parse(res.data.recordCount)[0].recordCount;
        dispatch(SET_RECORD_COUNT(draftCount));
        let draftDataRaw:any[]=[];
        const payload = {
            pageNumber:1,
            recordsPerPage:chunkSize
        }

        toastId = notifyLoader(`Downloading Data 0 / ${draftCount}`)

        if(draftCount <= chunkSize){
            const result = await getDraftById({id:draftDetails.DraftId,body:payload});
            const clonedData = _.cloneDeep(result.data[0]);
            draftDataRaw = [clonedData]
        }
        else{
            const numberOfPages = Math.ceil(draftCount/chunkSize);
            for(let i=1; i<=numberOfPages; i++){
                payload.pageNumber = i;
                const result = await getDraftById({id:draftDetails.DraftId,body:payload})
                draftDataRaw.push(result.data[0]);
                if(i===numberOfPages) toast.update(toastId,{render:`Downloading Data ${draftCount} / ${draftCount}`})
                else toast.update(toastId,{render:`Downloading Data ${i*chunkSize} / ${draftCount}`})
            }
        }
        toast.dismiss(toastId);

        notifyLoader("Getting Draft Ready")
    
        // toast.update(toastId,{render:"Getting Draft Ready"});
       
        const draftData:any[]=[];
        draftDataRaw.forEach((data: any) => {
            const masterIndex = draftData.findIndex((draftObj:any) => draftObj.MasterId === data.MasterId);
            
            if (masterIndex >= 0) {
              if (data.DataMaster) {
                draftData[masterIndex].DataMaster = [
                  ...(draftData[masterIndex].DataMaster || []), 
                  ...data.DataMaster
                ];
              }
            } else {
              draftData.push(_.cloneDeep(data));
            }
        });
        const draftDataInSequence:any[] = [];

        draftData.forEach((Master:any)=>{
          let DataInSequence:any[] =[];
          if(Master?.DataMaster!==undefined){
            DataInSequence = transformDataInSequencialFormat(Master.DataMaster);
          }
            draftDataInSequence.push({
                ...Master,
                DataMaster:DataInSequence
            })
        })    
 
        const mastersData= await getMasterUIConfiguration(getActionName(draftDetails.ActionType).value)

        toast.dismiss();

        const fields = mastersData.data.data
        const masterState = createMastersStateFromDraftData(draftDataInSequence,fields)
        const activeMaster = masterState.find((m:MDMMasterState)=>m.progress!=='submitted');

        dispatch(TOGGLE_SELECT_MASTER_SCREEN(false))
        dispatch(STORE_ALL_MASTERS(mapMasterToMasterState(fields)))
        dispatch(FILL_MASTERS(masterState))
        dispatch(SET_DRAFT_ID(draftDetails.DraftId))
        if(activeMaster){
            dispatch(UPDATE_ACTIVE_MASTER(masterState.indexOf(activeMaster)))
            dispatch(UPDATE_DATA_AVAILABILITY_STATUS(true))
        }
        
        dispatch(TOGGLE_UPLOAD_MODAL(false))
        navigate(`/mta/master-data-management/control-panel/${getActionName(draftDetails.ActionType).label}`, {
            state:{
                backUrl: "/mta/master-data-management/saved-drafts"
            }
        });

        toast.dismiss();
        notifySuccess("Draft Loaded Successfully");

       }catch(error:any){
        notifyError(error.message);
        toast.dismiss(toastId)
       }
    }


    const transformDataInSequencialFormat=(data:any)=>{
        return data.sort((a:any, b:any) => {
            const aHasError = a.error===undefined ? false : a.error.length > 0;
            const aHasWarning = a.warning===undefined ? false :  a.warning.length > 0;
            const bHasError = b.error===undefined ? false :  b.error.length > 0;
            const bHasWarning = b.warning===undefined ? false :  b.warning.length > 0;
       
            if (aHasError && aHasWarning && (!bHasError || !bHasWarning)) {
              return -1; // a should come before b
            }
            if (!aHasError && !aHasWarning && (bHasError || bHasWarning)) {
              return 1;  // b should come before a
            }
            if (aHasError && !bHasError) {
              return -1; // a should come before b
            }
            if (!aHasError && bHasError) {
              return 1;  // b should come before a
            }
            if (aHasWarning && !bHasWarning) {
              return -1; // a should come before b
            }
            if (!aHasWarning && bHasWarning) {
              return 1;  // b should come before a
            }
            return 0; // keep the order if they are the same in terms of presence
          });
    }


    
    const onDeleteDraft = async()=>{
        closeDeleteModal();
        await notifyPromise(
            deleteDraft(deleteDraftId),
            {
                pending:'Deleting Draft',
                success:'Draft has been deleted successfully',
                error:'Something went wrong'
            }
        )
        refetch();
    }

    return{
        isDeleteModalOpen,
        openDeleteModal,
        closeDeleteModal,
        onEditDraft,
        onDeleteDraft,
        allDrafts,
        isLoading
        
    }
}

export default useSavedDrafts
