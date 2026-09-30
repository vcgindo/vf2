import { useCallback, useEffect, useState } from "react"
import { useDispatch, useSelector } from "react-redux"
import { useNavigate } from "react-router"
import { notifyError, notifyLoader, notifySuccess } from "../../../../../helpers/notify"
import { useDeleteMTODraft, useGetAllDrafts, useGetBufferTypeMaster, useGetCCRMasterData, useGetDraftById, useGetDraftCount, useGetMasterUIConfiguration, useGetMTODraftById, useGetMTODrafts, useGetMTOMasterUIConfiguration } from "../../../../../VectorFlow/Services/MTA/MDM"

import { toast } from 'react-toastify'
import { v4 as uuidv4 } from "uuid"
import { useUserData } from "../../../../../context"
import { createMastersStateFromDraftData, generateRandomId, getActionName, getCCRNamesFromId, mapMasterToMasterState } from "../../../../../helpers/utils"
import { FILL_MASTERS, SET_DRAFT_ID, SET_RECORD_COUNT, STORE_ALL_MASTERS, TOGGLE_SELECT_MASTER_SCREEN, TOGGLE_UPLOAD_MODAL, UPDATE_ACTIVE_MASTER, UPDATE_DATA_AVAILABILITY_STATUS } from "../../../../../redux/actions/MDM"
import { SET_BUFFER_MODIFY_DATA, SET_CCR_MODIFY_DATA, SET_POOGI_MODIFY_DATA } from "../../../../../redux/actions/MTO"
import type { RootState } from '../../../../../redux/store/store'
import { useGetDeptMasterData, useGetPlantMasterData } from "../../../../../VectorFlow/Services/MTO/Common/Masters"
import { useGetCCRGroupMaster } from "../../../../../VectorFlow/Services/MTO/Production/DueDateQuotation"
import { MDMMasterState } from "../../../../../VectorFlow/types/MDM"
import DaysOfWeekRenderer from "../ViewModify/DaysOfWeekRenderer"
import MTOErrorWarningCell from "../ViewModify/MTOErrorWarningCell"
import { convertDateFormat } from "../ViewModify/CommonUtils"



const useSavedDrafts = ()=>{

    const dispatch = useDispatch()
    const navigate = useNavigate()
    const { mutateAsync: getCCRMasterData } = useGetCCRMasterData();
    const {mutateAsync:getDraftById} = useGetDraftById()
    const {mutateAsync:getMasterUIConfiguration} = useGetMasterUIConfiguration()
    const {mutateAsync:deleteDraft} = useDeleteMTODraft()
    const [isDeleteModalOpen,toggleDeleteModal] = useState<boolean>(false)
    const [deleteDraftId,setDeleteDraftId] = useState<string>("");
    const {mutateAsync:getDraftCount} = useGetDraftCount();
    const chunkSize = useSelector((state:RootState) => state.mdm.chunkSize)
    const [allDrafts, setAllDrafts] = useState<any>([]);
    const {mutateAsync: getMtoDrafts, isLoading} = useGetMTODrafts();
    const {mutateAsync: getDraftByIdMTO} = useGetMTODraftById();
    const {mutateAsync: getMTOMasterUIConfiguration} = useGetMTOMasterUIConfiguration();
    const closeDeleteModal =()=>toggleDeleteModal(false)

    const {mutateAsync: GetBufferTypeMaster} = useGetBufferTypeMaster();
    const {mutateAsync: getPlantMaster} = useGetPlantMasterData();
    const {mutateAsync: getDeptMaster} = useGetDeptMasterData();
    const {mutateAsync: getCCRGroupMaster} = useGetCCRGroupMaster();
    const [plantMaster, setPlantMaster] = useState<any>();
    const [deptMaster, setDeptMaster] = useState<any>();
    const [ccrGroupMaster, setCcrGroupMaster] = useState<any>();
    const [bufferTypeMaster, setBufferTypeMaster] = useState<any>();
    const [ccrsData,setCcrsData] = useState<any>();
    
    const user = useUserData();
    
    const getCombinedMTOData = async()=>{
        try{
            // TODO: change the data to userid later now data is available for this
            const response:any = await getMtoDrafts(user.user.user.id);
            const draftData:any = [];
            response.data.data.forEach((draft: any)=>{
                // const date = new Date(draft.co);
                const newData = {
                    DraftId: draft.did,
                    ActionType: draft.at,
                    LastModifiedDateTime: convertDateFormat(draft.co.toString()),
                    Masters: draft.at +" - "+ draft.mnm,
                    SearchKeys: draft.sk,
                    userid: draft.uid,
                    isMTO: true,
                    mid: draft.mid,
                    dnm: draft.dnm
                }
                draftData.push(newData);
            })
            
            setAllDrafts(draftData);
            
        }
        catch(error){
            console.error(error)
        }
    }
    
    
    
    useEffect(() => {
      getCombinedMTOData();
    }, []);
    
    const openDeleteModal = (draftId:string)=>{
        setDeleteDraftId(draftId)
        toggleDeleteModal(true)
    }
    
    

    const getInitalData = async () => {
        try {
            const [
                bufferTypeResponse,
                ccrGroupResponse,
                deptResponse,
                plantResponse,
                ccrs
            ] = await Promise.all([
                GetBufferTypeMaster(),
                getCCRGroupMaster(),
                getDeptMaster(),
                getPlantMaster(),
                getCCRMasterData({})
            ]);
    
            setBufferTypeMaster(bufferTypeResponse?.data?.data);
            setCcrGroupMaster(ccrGroupResponse?.data?.data);
            setDeptMaster(deptResponse?.data?.data);
            setPlantMaster(plantResponse?.data?.data);
            setCcrsData(ccrs.data?.data || []);
    
        } catch (error) {
            console.error("Error fetching initial data:", error);
        }
    };
    
    useEffect(()=>{
        getInitalData();
    },[])

    
    const convertToColDefs = useCallback(((data:any,draftDetails:any) => {
      const { ActionType } = draftDetails;
      const newColDef =  data
        .sort((a:any, b:any) => (a.col_Position || 0) - (b.col_Position || 0))
        .map((item: any) => ({
          field: item?.key,                    // Use the "key" as the "field"
          colId: item?.key,                    // Also set "colId" from "key"
          headerName: item?.displayName,        // Set "headerName" from "displayName"
          // floatingFilter: false,              // Set default values for additional properties
          editable: (ActionType == "Modify") ? false : true
        }));

      const colDef = newColDef.map((col:any)=>{
          if (col.field === 'pl' || col.field === 'plnm') return {
              ...col,
              editable: (ActionType == "Modify") ? false : true,
              cellEditor: 'agRichSelectCellEditor',
              cellEditorParams: {
                values: plantMaster?.map((item: any) => item.plant_name),
              },
            };

            if(col.field === 'actions' || col.field === 'iv'){
              return {
                ...col,
                editable: false,
                filter: false,
                floatingFilter: false,
              }
            }

            if (col.field === 'dp') return {
              ...col,
              editable: (ActionType == "Modify") ? false : true,
              cellEditor: 'agRichSelectCellEditor',
              cellEditorParams: {
                values: deptMaster?.map((item: any) => item.dept_name),
              },
            };
            
            if (col.field === 'cgid') return {
              ...col,
              editable: (ActionType == "Modify") ? false : true,
              cellEditor: 'agRichSelectCellEditor',
              cellEditorParams: {
                values: Object.keys(ccrGroupMaster || {}),
              },
            };
            if (col.field === "bt")
              return {
                ...col,
                cellEditor: "agRichSelectCellEditor",
                editable: ActionType == "Modify" ? false : true,
                cellEditorParams: {
                  values: bufferTypeMaster?.map((item: any) => item.nm),
                },
              };
            if(col.field === "dow"){
              return {
                  ...col,
                  cellRenderer: DaysOfWeekRenderer
              }
            }
            if(col.field === "ccr_id"){
              return {
                  ...col,
                  valueFormatter :(params:any)=>{
                      return getCCRNamesFromId(ccrsData,params.data.ccr_id)
                  }
              }
            }
            else return col;
      })

      if(ActionType !== 'Modify'){
        return colDef.filter((col:any)=> col.field !== 'iv')
      }

      return colDef
    }),[plantMaster,ccrGroupMaster, bufferTypeMaster,ccrsData, deptMaster])
      
      const convertToPoogiDraftData = (data: any, page: any) => {
        const result: any[] = [];
      
        data.forEach((item: any) => {
          const tempMajId = "maj_" + uuidv4();
          
          // Create a shallow copy of the item to avoid modifying the original object
          const copiedItem = { ...item };
      
          if (page === "Modify") {
            // Ensure majId is set
            copiedItem.majId = copiedItem?.majId || tempMajId;
      
            // Ensure minId is set for each minData item
            if (copiedItem.minData && Array.isArray(copiedItem.minData)) {
              copiedItem.minData = copiedItem.minData.map((minItem: any) => {
                // Create a shallow copy of minItem
                const copiedMinItem = { ...minItem };
                copiedMinItem.minId = copiedMinItem?.minId || "min_" + uuidv4();
                return copiedMinItem;
              });
            }
      
            result.push(copiedItem); // Add the modified item
          } else {
            // Handle other page types
            if (item.minData && Array.isArray(item.minData)) {
              const tempMinId = "min_" + uuidv4();
      
              item.minData.forEach((minItem: any) => {
                result.push({
                  majdsc: item.majdsc,
                  majId: minItem?.majId || tempMajId,
                  minId: minItem?.minId || tempMinId,
                  mindsc: minItem.mindsc,
                  mintid: minItem.mintid,
                  mincd: minItem.mincd,
                  plnm: item.plnm,
                  ie: minItem.ie || false,
                  id: minItem.id || false,
                  iu: minItem.iu || false,
                  pl: item.pl,
                  aon: minItem.aon,
                  aid: minItem.aid,
                  anm: minItem.anm,
                  st: minItem.st,
                  stnm: minItem.stnm,
                });
              });
            }
          }
        });

      
        return result;
      };
      
    
    const onEditDraft = async (draftDetails: any) => {
      let toastId;
      if (draftDetails.isMTO) {
        try {
          const res: any = await getDraftByIdMTO({
            draftId: draftDetails.DraftId,
            mid: draftDetails.mid,
          });
          let draftData: any = res.data.data;
          if(draftDetails.mid !== 503 && draftDetails.mid !== 504){
              draftData = draftData.map((item:any)=> {
                // this is for ccr and buffer that are already added and that dont required action buttons 
                if(item.bid || item.cid){
                  return item
                }else{
                 return {...item, editable:false,ia:true,isdel:false,id:uuidv4()}
                }
              });
          }
          dispatch(SET_RECORD_COUNT(draftData.length));

          const mastersDataRes = await getMTOMasterUIConfiguration();
          const mastersData = mastersDataRes?.data?.data?.find(
            (item: any) => item.id === draftDetails.mid
          );
          toast.dismiss();

          const fields = mastersData.fields;

          if (draftDetails.mid === 501) {
            dispatch(SET_BUFFER_MODIFY_DATA(draftData));
          }
          if (draftDetails.mid === 502) {
            dispatch(SET_CCR_MODIFY_DATA(draftData));
          }
          if (draftDetails.mid === 503) {
            dispatch(
              SET_POOGI_MODIFY_DATA(
                convertToPoogiDraftData(draftData, draftDetails.ActionType)
              )
            );
          }

          const masterState: any = [
            {
              isMTO: true,
              id: draftDetails.mid,
              name: draftDetails.dnm,
              colDefs: [
                ...convertToColDefs(fields, draftDetails),
                {
                  colId: "err",
                  colPosition: 100,
                  field: "err",
                  cellRenderer: MTOErrorWarningCell,
                  headerName: "Error",
                  pinned: "left",
                  minWidth: 300
                },
              ],
              rowData:
                draftDetails.mid !== 503
                  ? draftData
                  : convertToPoogiDraftData(draftData, draftDetails.ActionType),
              isChecked: true,
              filters: [
                {
                  id: generateRandomId(),
                  masterId: draftDetails.mid,
                  field: "",
                  operator: "",
                  text: "",
                },
              ],
              progress: "view",
              fields: fields,
            },
          ];

          if (draftDetails.isMTO && draftDetails.ActionType === "Modify") {
            masterState[0].colDefs = [
              ...convertToColDefs(fields, draftDetails),
            ];
          }

          dispatch(TOGGLE_UPLOAD_MODAL(false));

          dispatch(TOGGLE_SELECT_MASTER_SCREEN(false));
          dispatch(FILL_MASTERS(masterState));
          dispatch(SET_DRAFT_ID(draftDetails.DraftId));
          dispatch(UPDATE_DATA_AVAILABILITY_STATUS(true));
          dispatch(UPDATE_ACTIVE_MASTER(0));       
          if (draftDetails.ActionType == "Modify") {
            navigate(`/mto/master-data-management/control-panel/view-modify`,{
              state:{
                backUrl : '/mto/master-data-management/saved-drafts',
                draftId: draftDetails.DraftId,
              }
            });
          } else if (draftDetails.ActionType === "Add") {
            navigate(
              `/mto/master-data-management/control-panel/${draftDetails.ActionType.toLowerCase()}`,
              {
                state:{
                  backUrl : '/mto/master-data-management/saved-drafts',
                  draftId: draftDetails.DraftId,
                }
              }
            );
          } else {
            navigate(
              `/mto/master-data-management/control-panel/${draftDetails.ActionType.toLowerCase()}`,{
                state:{
                  backUrl : '/mto/master-data-management/saved-drafts',
                  draftId: draftDetails.DraftId,
                }
              }
            );
          }
          toast.dismiss();
          notifySuccess("Draft Loaded Successfully");

        } catch (error) {
          console.error(error);
        }

        return;
      }

      try {
        const res: any = await getDraftCount(draftDetails.DraftId);
        const draftCount = JSON.parse(res.data.recordCount)[0].recordCount;
        dispatch(SET_RECORD_COUNT(draftCount));
        let draftDataRaw = [];
        const payload = {
          pageNumber: 1,
          recordsPerPage: chunkSize,
        };

        toastId = notifyLoader(`Downloading Data 0 / ${draftCount}`);

        if (draftCount <= chunkSize) {
          const result = await getDraftById({
            id: draftDetails.DraftId,
            body: payload,
          });
          draftDataRaw = result.data.data;
        } else {
          const numberOfPages = Math.ceil(draftCount / chunkSize);
          for (let i = 1; i <= numberOfPages; i++) {
            payload.pageNumber = i;
            const result = await getDraftById({
              id: draftDetails.DraftId,
              body: payload,
            });
            draftDataRaw.push(...result.data.data);
            if (i === numberOfPages)
              toast.update(toastId, {
                render: `Downloading Data ${draftCount} / ${draftCount}`,
              });
            else
              toast.update(toastId, {
                render: `Downloading Data ${i * chunkSize} / ${draftCount}`,
              });
          }
        }
        toast.dismiss(toastId);

        notifyLoader("Getting Draft Ready");

        // toast.update(toastId,{render:"Getting Draft Ready"});

        const draftData: any = [];
        draftDataRaw.forEach((data: any) => {
          const masterIndex = draftData.findIndex(
            (draftObj: any) => draftObj.MasterId == data.MasterId
          );
          if (masterIndex >= 0) {
            if ("DataMaster" in data) {
              draftData[masterIndex].DataMaster = [
                ...draftData[masterIndex].DataMaster,
                ...data.DataMaster,
              ];
            }
            return;
          } else {
            draftData.push(data);
          }
        });

        const mastersData = await getMasterUIConfiguration(
          getActionName(draftDetails.ActionType).value
        );

        toast.dismiss();

        const fields = mastersData.data.data;
        const masterState = createMastersStateFromDraftData(draftData, fields);
        const activeMaster = masterState.find(
          (m: MDMMasterState) => m.progress !== "submitted"
        );

        dispatch(TOGGLE_SELECT_MASTER_SCREEN(false));
        dispatch(STORE_ALL_MASTERS(mapMasterToMasterState(fields)));
        dispatch(FILL_MASTERS(masterState));
        dispatch(SET_DRAFT_ID(draftDetails.DraftId));
        if (activeMaster) {
          dispatch(UPDATE_ACTIVE_MASTER(masterState.indexOf(activeMaster)));
          dispatch(UPDATE_DATA_AVAILABILITY_STATUS(true));
        }
        navigate(
          `/master-data-management/control-panel/${
            getActionName(draftDetails.ActionType).label
          }`
        );
        toast.dismiss();
        notifySuccess("Draft Loaded Successfully");
      } catch (error: any) {
        notifyError(error.message);
        toast.dismiss(toastId);
      }
    };
    
    const onDeleteDraft = async()=>{

        try{
            const response = await deleteDraft(deleteDraftId);
            if(response.status===200){
                toast.dismiss();
                notifySuccess("Draft deleted!");
                setAllDrafts(allDrafts.filter((ele:any)=>{return( ele.DraftId!==deleteDraftId)}))
                closeDeleteModal();
            }
            else{
                notifyError("Failed to delete draft");
            }
        }
        catch(e){
            toast.dismiss()
            notifyError("Failed to delete draft!");
        }
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
