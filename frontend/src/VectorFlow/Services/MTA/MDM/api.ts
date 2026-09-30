/* eslint-disable @typescript-eslint/no-namespace */
import axios, { AxiosResponse } from 'axios'
import { GetMasterDataPayload } from '../../../types/MDM';


export namespace MDMService {

  export const getMasterUIConfiguration = async (screenType:string) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetMasterUIConfiguration`,{screenType:screenType});
  }

  export const getCount = async (body:GetMasterDataPayload) => {
   
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetCount`,body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getRetailCount = async (body: GetMasterDataPayload) => {

    return await axios.post(process.env.REACT_APP_API_HOST + `/api/validate-master/get-count/`, body, {
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getMasterData = async (body:GetMasterDataPayload) => {
   
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetMasterData`,body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getMasterDataRetail = async (body: GetMasterDataPayload) => {

    return await axios.post(process.env.REACT_APP_API_HOST + `/api/validate-master/get-master-data/`, body, {
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getAllDrafts = async () => {
      return await axios.get(process.env.REACT_APP_API_HOST + `api/mta/allDrafts`,{
        headers: { 'Content-Type': 'application/json' }
      }).catch((err)=>{
        console.log(err);
        return {} as AxiosResponse
      })
    }

  export const getDraftCount = async(id:string)=>{
    return await axios.get(process.env.REACT_APP_API_HOST + `api/mta/draftCount/${id}`,{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getDraftById = async(id:string,body:any)=>{
    const result =  await axios.post(process.env.REACT_APP_API_HOST + `api/mta/draft/${id}`,body,{
      headers: { 'Content-Type': 'application/json'  },
      responseType: 'text'
    })
    const responseJson = JSON.parse(result.data)
    return responseJson
  }

  export const createDraft = async (body: any) => {
    return axios.post(process.env.REACT_APP_API_HOST + `api/mta/draft`,body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const modifyDraft = async (body: any) => {
    return axios.put(process.env.REACT_APP_API_HOST + `api/mta/draft`,body,{
      headers: { 'Content-Type': 'application/json' },
    })
  }

  export const deleteDraft = async(id:string)=>{
    return await axios.delete(process.env.REACT_APP_API_HOST + `api/mta/draft/${id}`,{
      headers: { 'Content-Type': 'application/json' }
    })
  }
  export const deleteMTODraft = async(did:string)=>{
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/DeleteDraft/`,
    {did}
    )
  }

  export const getSeasonalityDetails = async (body:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + 'api/mta/GetSeasonalityDetails',body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }
  
  export const getPendingTasks = async()=>{
    return await axios.get(process.env.REACT_APP_API_HOST + `api/mta/GetTaskPendingForReviewData`,{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getTaskDetails = async(body:{taskId:string,paginationParameter:{pageNumber:number,recordsPerPage:number}})=>{
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetTaskDetails`,body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getTaskCount = async(taskId:string)=>{
    return await axios.get(process.env.REACT_APP_API_HOST + `api/mta/GetTaskCount/${taskId}`,{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getTaskStatusData = async()=>{
    return await axios.get(process.env.REACT_APP_API_HOST + `api/mta/GetTaskStatusData`,{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getTaskDetailsDownloadData = async(body:{taskId:string,approverId:number})=>{
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetTaskDetailsDownloadData`,JSON.stringify(body),{
      headers: { 'Content-Type': 'application/json' }
    })
  }


  export const modifyMasterData = async(body:any)=>{
    return await axios.post(process.env.REACT_APP_API_HOST + 'api/mta/ModifyMasterData',{...body,"forwardUsers":true},{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const modifyMasterDataRetail = async (body: any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `/api/validate-master/modify-master-data/`, body, {
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const addMasterData = async(body:any)=>{
    return await axios.post(process.env.REACT_APP_API_HOST + 'api/mta/AddMasterData',{...body,"forwardUsers":true},{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const addMasterDataRetail = async (body: any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `/api/validate-master/add-valid-master/`, body, {
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const deleteMasterData = async(body:any)=>{
    return await axios.post(process.env.REACT_APP_API_HOST + 'api/mta/RemoveMasterData',{...body,"forwardUsers":true},{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const deleteMasterDataRetail = async (body: any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `/api/validate-master/remove-master-data/`, body, {
      headers: { 'Content-Type': 'application/json' }
    })
  }


  export const deleteTask = async(taskId:any)=>{
    return await axios.delete(process.env.REACT_APP_API_HOST + 'api/mta/DeleteTask',{params:{taskId}})
  }

  export const approveTask = async(body:any)=>{
    return await axios.post(process.env.REACT_APP_API_HOST + 'api/mta/PostMasterAfterApproved',body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const validateMaster = async (formData: any, masterId: any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + 'api/validate-master/basic-validation/' + masterId, formData, {
      responseType: 'stream'
    })
  }

  export const getSkuLoc = async (body:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetSkuLoc`,body);
  }

  export const getTaskMastersHistory = async (body:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetTaskMastersHistory`,body);
  }

  export const getUploadProgress = async (processId: any) => {
    return await axios.get(process.env.REACT_APP_API_HOST + 'api/validate-master/get-upload-progress/' + processId, {
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getAllReports = async()=>{
    return await axios.get(process.env.REACT_APP_API_HOST + 'api/mta/GetAllReports',{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getAllEnvironmentConfiguration = async()=>{
    return await axios.get(process.env.REACT_APP_API_HOST + 'api/mta/GetEnvironmentConfiguration',{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const editEnvironmentConfiguration = async(body:any)=>{
    return await axios.put(process.env.REACT_APP_API_HOST + 'api/mta/EditEnvironmentConfiguration',body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getAllUIReportConfiguration = async()=>{
    return await axios.get(process.env.REACT_APP_API_HOST + 'api/mta/GetAllUIReportConfig',{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getAllUIMDMConfiguration = async()=>{
    return await axios.get(process.env.REACT_APP_API_HOST + 'api/mta/GetAllUIMDMConfig',{
      headers: { 'Content-Type': 'application/json' }
    })
  }
  export const useGetAllAdminPermissions = async()=>{
    return await axios.get(process.env.REACT_APP_API_HOST + 'api/mta/GetAllPermissionsAdmin',{
      headers: { 'Content-Type': 'application/json' }
    })
  }
  
  export const useAddProductPermissions = async(body:any)=>{
    return await axios.post(process.env.REACT_APP_API_HOST + 'api/mta/AddPermissionsAdmin',body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const useAddLocationPermissions = async(body:any)=>{
    return await axios.post(process.env.REACT_APP_API_HOST + 'api/mta/AddPermissionsAdmin',body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const useBulkUploadPermission = async (formData: FormData) => {
    return await axios.post(process.env.REACT_APP_API_HOST + 'api/mta/BulkUploadPermissions', formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    });
  };

  export const useEditReportConfiguration = async(body:any)=>{
    return await axios.put(process.env.REACT_APP_API_HOST + 'api/mta/UpdateUIReportConfig',body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }
  
  export const useEditMDMConfiguration = async(body:any)=>{
    return await axios.put(process.env.REACT_APP_API_HOST + 'api/mta/UpdateUIMDMConfig',body,{
      headers: { 'Content-Type': 'application/json' }
    })
  }
  

  /**This get the  MTO Masters Data*/
  export const getMTOMastersData = async () => {
    return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + '/GetMasterManagementData/', {
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getMTOTaskStatusData = async () => {
    return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + '/GetTasks/', {
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const putMTOAddBufferMaster = async (body:any)=>{
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + '/AddBufferMaster/', body )
  }
  export const putMTOAddPoogiMaster = async (body:any)=>{
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + '/AddPOOGIReasonMaster/', body )
  }
  export const putMTOAddCCRMaster = async (body:any)=>{
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + '/AddCCRMaster/', body )
  }

  export const putMTOAddCalendarMaster = async (body:any)=>{
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + '/AddCalendarMaster/', body )
  }

  export const getMTOTaskById = async (taskId: string, mmid: string) => {
    return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/GetTaskById/?tid=${taskId}&mmid=${mmid}`, {
      headers: { 'Content-Type': 'application/json' }
    })
  }

  /** Save buffer master task MTO */
  export const saveBufferMasterTask = async (body: any) => {
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + '/SaveBufferMasterTask/?forwardUsers=true', 
      body
    )
  }

  export const saveCalendarMasterTask = async (body:any) => {
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + "/SaveCalendarTask/?forwardUsers=true", body)
  }

  export const saveCalendarMasterDraft = async (body:any) => {
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + "/SaveCalendarMasterDraft/",body)
  }

  export const savePOOGIMasterTask = async (body: any) => {
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + '/SavePoogiReasonMasterTask/?forwardUsers=true', 
      body
    )
  }
  export const savePOOGIMasterDraft = async (body: any) => {
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + '/SavePoogiReasonDraft/', 
      body
    )
  }
  export const saveCCRMasterTask = async (body: any) => {
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + '/SaveCCRMasterTask/?forwardUsers=true', 
      body
    )
  }
  export const saveBufferMasterDraft = async (body: any) => {
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + '/SaveBufferMasterDraft/', 
      body
    )
  }
  export const saveCCRMasterDraft = async (body: any) => {
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + '/SaveCCRMasterDraft/', 
      body
    )
  }

  export const getBufferMasterData = async (body:any) => {
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + '/GetBufferMasterForMasterMgmt/?masterId=501',body.finPayload? body.finPayload: {});
  }

  export const getCCRMasterData = async (body:any)=>{
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + '/GetCCRMasterForMasterMgmt/?masterId=502', body.finPayload? body.finPayload: {})
  }

  export const getPOOGIMasterData = async (body:any)=>{
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + '/GetPoogiReasonMasterForMasterMgmt/?masterId=503', body.finPayload? body.finPayload: {})
  }
  export const getCalendarMasterData = async ()=>{
    return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + '/GetCalendarDataForMasterMgmt/?masterId=504', {
      headers: { 'Content-Type': 'application/json' }
    })
  }



  export const getBufferTypeMaster = async () => {
    return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + '/GetBufferTypeMaster/', {
      headers: { 'Content-Type': 'application/json' }
    })
  }

  export const getMTODrafts = async (uid: any)=>{
    return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/GetDraftInstances/?uid=${uid}`)
  }

  export const getMTODraftById = async (id: any, mid: any)=>{
    if(mid===501){
      return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/GetBufferDraftData/?did=${id}&mid=501`)
    }
    else if(mid===502){
      return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/GetCCRDraftData/?did=${id}&mid=502`)
    }
    else if(mid===503){
      return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO+ `/GetPoogiReasonDraftData/?did=${id}&mid=503`)
    }else if(mid === 504){
      return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/GetCalendarMasterDraft/?did=${id}&mid=504`)
    }
  }

  export const getAllUsers = async()=>{
    return await axios.get(process.env.REACT_APP_API_HOST + `/api/user/all-users/`)
  }


  export const getMaxFolDate = async()=>{
    return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getMaxFolDateForCcr/`,{
      headers: { 'Content-Type': 'application/json' }
    })
  }

  
  export const getApproverNames = async (params:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/user/get-approver-names/`,{...params})
  }
}

