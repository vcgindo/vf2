import { useQuery, useMutation } from '@tanstack/react-query'
import { GetMasterDataPayload } from '../../../types/MDM';
import { MDMService } from './api'


export const QUERY_KEYS = {
  useGetMasterUIConfiguration: ['MDMService.useGetMasterUIConfiguration'],
  useGetMasterData: ['MDMService.useGetMasterData'],
  useGetAllDrafts: ['MDMService.useGetAllDrafts'],
  useGetDraftCount: ['MDMService.useGetDraftCount'],
  useGetDraftById: ['MDMService.useGetDraftById'],
  useCreateDraft: ['MDMService.useCreateDraft'],
  useModifyDraft: ['MDMService.useModifyDraft'],
  useDeleteDraft: ['MDMService.useDeleteDraft'],
  useGetSeasonalityDetails: ['MDMService.useGetSeasonalityDetails'],
  useGetPendingTasks: ['MDMService.useGetPendingTasks'],
  useGetTaskStatusData: ['MDMService.useGetTaskStatusData'],
  useModifyMasterData: ['MDMService.useModifyMasterData'],
  useDeleteTask: ['MDMService.useDeleteTask'],
  useApproveTask: ['MDMService.useApproveTask'],
  usegetSkuLoc: ['MDMService.useGetSkuLoc'],
  usegetTaskMastersHistory: ['MDMService.useGetTaskMastersHistory'],
  useGetUploadProgress: ['MDMService.useGetUploadProgress'],
  useGetAllReports: ['MDMService.useGetAllReports'],
  useGetAllEnvironmentConfiguration: ['MDMService.useGetAllEnvironmentConfiguration'],
  useEditEnvironmentConfiguration: ['MDMService.useEditEnvironmentConfiguration'],
  useGetAllUIReportConfiguration:['MDMService.useGetAllUIReportConfiguration'],
  useGetAllUIMDMConfiguration:['MDMService.useGetAllUIMDMConfiguration'],
  useGetAllAdminPermissions:['useGetAllAdminPermissions'],
  useAddProductPermissions:['useAddProductPermissions'],
  useAddLocationPermissions:['useAddLocationPermissions'],
  useEditReportConfiguration:['useEditReportConfiguration'],
  useEditMDMConfiguration:['useEditMDMConfiguration'],
  useGetMTOPendingTask: ['MDMService.useGetMTOPendingTask']
}


export const useGetMasterUIConfiguration = () => {
  return useMutation(async (screenType: string) => {
    return await MDMService.getMasterUIConfiguration(screenType);
  });
}

export const useGetCount = () => {
  return useMutation(async (body: GetMasterDataPayload) => {
    return await MDMService.getCount(body)
  })
}

export const useGetRetailCount = () => {
  return useMutation(async (body: GetMasterDataPayload) => {
    return await MDMService.getRetailCount(body)
  })
}

export const useGetMasterData = () => {
  return useMutation(async (body: GetMasterDataPayload) => {
    return await MDMService.getMasterData(body)
  })
}

export const useGetMasterDataRetail = () => {
  return useMutation(async (body: GetMasterDataPayload) => {
    return await MDMService.getMasterDataRetail(body)
  })
}

export const useGetAllDrafts = () => {
  return useQuery(QUERY_KEYS.useGetAllDrafts, async () => {
    return await MDMService.getAllDrafts()
  })
}

export const useGetDraftCount = () => {
  return useMutation(QUERY_KEYS.useGetDraftCount, async (id: string) => {
    return await MDMService.getDraftCount(id)
  })
}

export const useGetDraftById = () => {
  return useMutation(QUERY_KEYS.useGetDraftById, async (payload: any) => {
    const { id, body } = payload;
    return await MDMService.getDraftById(id, body)
  })
}

export const useCreateDraft = () => {
  return useMutation(async (body: any) => {
    return await MDMService.createDraft(body)
  })
}

export const useModifyDraft = () => {
  return useMutation(async (body: any) => {
    return await MDMService.modifyDraft(body)
  })
}

export const useDeleteDraft = () => {
  return useMutation(async (id: string) => {
    return await MDMService.deleteDraft(id)
  })
}


export const useDeleteMTODraft = () => {
  return useMutation(async (id: string) => {
    return await MDMService.deleteMTODraft(id)
  })
}

export const useGetSeasonalityDetails = () => {
  return useMutation(QUERY_KEYS.useGetSeasonalityDetails, async (body: object) => {
    return await MDMService.getSeasonalityDetails(body)
  })
}

export const useGetPendingTasks = () => {
  return useQuery(QUERY_KEYS.useGetPendingTasks, async () => {
    return await MDMService.getPendingTasks()
  })
}

export const useGetTaskCount = () => {
  return useMutation(async (taskId: string) => {
    return await MDMService.getTaskCount(taskId)
  })
}

export const useGetTaskDetails = () => {
  return useMutation(async (body: { taskId: string, paginationParameter: { pageNumber: number, recordsPerPage: number } }) => {
    return await MDMService.getTaskDetails(body)
  })
}

export const useGetTaskStatusData = () => {
  return useQuery(QUERY_KEYS.useGetTaskStatusData, async () => {
    return await MDMService.getTaskStatusData()
  })
}

export const useGetMTOTaskStatusData = () => {
  return useMutation(async () => {
    return await MDMService.getMTOTaskStatusData();
  })
}

export const useGetMTOPendingTaskData = () => {
  return useQuery(QUERY_KEYS.useGetMTOPendingTask, async () => {
    return await MDMService.getMTOTaskStatusData();
  })
}

export const useGetMTOTaskById = () => {
  return useMutation(async ({taskId, mmid}:{taskId:string, mmid: string})=>{
    return await MDMService.getMTOTaskById(taskId, mmid);
  })
}

export const useGetTaskDetailDownloadData = () => {
  return useMutation(async (body: { taskId: string, approverId: number }) => {
    return await MDMService.getTaskDetailsDownloadData(body)
  })
}

export const useApproveTask = () => {
  return useMutation(async (body: { taskId: string, data: any }) => {
    return await MDMService.approveTask(body)
  })
}

export const useRemoveMasterData = () => {
  return useMutation(async (body: any) => {
    return await MDMService.deleteMasterData(body)
  })
}

export const useModifyMasterData = () => {
  return useMutation(async (body: any) => {
    return await MDMService.modifyMasterData(body)
  })
}

export const useModifyMasterDataRetail = () => {
  return useMutation(async (body: any) => {
    return await MDMService.modifyMasterDataRetail(body)
  })
}

export const useAddMasterData = () => {
  return useMutation(async (body: any) => {
    return await MDMService.addMasterData(body)
  })
}

export const useAddMasterDataRetail = () => {
  return useMutation(async (body: any) => {
    return await MDMService.addMasterDataRetail(body)
  })
}

export const useDeleteMasterData = () => {
  return useMutation(async (body: any) => {
    return await MDMService.deleteMasterData(body)
  })
}

export const useDeleteMasterDataRetail = () => {
  return useMutation(async (body: any) => {
    return await MDMService.deleteMasterDataRetail(body)
  })
}

export const useDeleteTask = () => {
  return useMutation(async (taskId: any) => {
    return await MDMService.deleteTask(taskId)
  })
}

export const useValidateMaster = () => {
  return useMutation(async (body: any) => {
    const { formData, masterId } = body;
    return await MDMService.validateMaster(formData, masterId)
  })
}

export const useGetSkuLoc = () => {
  return useMutation(async (body: any) => {
    return await MDMService.getSkuLoc(body)
  })
}

export const useGetTaskMastersHistory = () => {
  return useMutation(async (body: any) => {
    return await MDMService.getTaskMastersHistory(body)
  })
}
export const useGetUploadProgress = () => {
  return useMutation(QUERY_KEYS.useGetUploadProgress, async (processId: any) => {
    return await MDMService.getUploadProgress(processId)
  })
}

export const useGetAllReports = () => {
  return useMutation(QUERY_KEYS.useGetAllReports, async () => {
    return await MDMService.getAllReports()
  })
}

export const useGetAllEnvironmentConfiguration = () => {
  return useMutation(QUERY_KEYS.useGetAllEnvironmentConfiguration, async () => {
    return await MDMService.getAllEnvironmentConfiguration()
  })
}

export const useEditEnvironmentConfiguration = () => {
  return useMutation(QUERY_KEYS.useEditEnvironmentConfiguration, async (body:any) => {
    return await MDMService.editEnvironmentConfiguration(body)
  })
}

export const useGetAllUIReportConfiguration = () => {
  return useMutation(QUERY_KEYS.useGetAllUIReportConfiguration, async () => {
    return await MDMService.getAllUIReportConfiguration()
  })
}

export const useGetAllUIMDMConfiguration = () => {
  return useMutation(QUERY_KEYS.useGetAllUIMDMConfiguration, async () => {
    return await MDMService.getAllUIMDMConfiguration()
  })
}

export const useGetAdminPermissions = () => {
  return useMutation(QUERY_KEYS.useGetAllAdminPermissions, async () => {
    return await MDMService.useGetAllAdminPermissions()
  })
}

export const useAddProductPermissions = () => {
  return useMutation(QUERY_KEYS.useAddProductPermissions, async (body:any) => {
    return await MDMService.useAddProductPermissions(body)
  })
}

export const useAddLocationPermissions = () => {
  return useMutation(QUERY_KEYS.useAddLocationPermissions, async (body:any) => {
    return await MDMService.useAddLocationPermissions(body)
  })
}

export const useBulkUploadPermissions= () => {
  return useMutation(async (body: any) => {
    return await MDMService.useBulkUploadPermission(body)
  })
}

export const useEditReportConfiguration = () => {
  return useMutation(QUERY_KEYS.useEditReportConfiguration, async (body:any) => {
    return await MDMService.useEditReportConfiguration(body)
  })
}

export const useEditMDMConfiguration = () => {
  return useMutation(QUERY_KEYS.useEditMDMConfiguration, async (body:any) => {
    return await MDMService.useEditMDMConfiguration(body)
  })
}


/**Adding the MTO Masters related calls */
export const useGetMTOMasterUIConfiguration = () => {
  return useMutation(async () => {
    return await MDMService.getMTOMastersData()
  })
}

/** View and modify save data MTO */
export const useSaveBufferMasterTask = () => {
  return useMutation(async (body: any) => {
    return await MDMService.saveBufferMasterTask(body)
  })
}

// view and modify save calendar task
export const useSaveCalendarMasterTask = () => {
  return useMutation(async (body:any)=>{
    return await MDMService.saveCalendarMasterTask(body)
  })
}

export const useSaveCalendarMasterDraft = ()=>{
  return useMutation(async (body:any)=>{
    return await MDMService.saveCalendarMasterDraft(body);
  })
}

export const useSaveCCRMasterTask = () => {
  return useMutation(async (body: any) => {
    return await MDMService.saveCCRMasterTask(body)
  })
}

export const useSavePOOGIMasterTask = ()=>{
  return useMutation(async (body: any)=>{
    return await MDMService.savePOOGIMasterTask(body);
  })
}
export const useSavePOOGIMasterDraft= ()=>{
  return useMutation(async (body: any)=>{
    return await MDMService.savePOOGIMasterDraft(body);
  })
}
export const useSaveBufferMasterDraft = () => {
  return useMutation(async (body: any) => {
    return await MDMService.saveBufferMasterDraft(body)
  })
}

export const useSaveCCRMasterDraft = () => {
  return useMutation(async (body: any) => {
    return await MDMService.saveCCRMasterDraft(body)
  })
}

export const usePutMtoBufferMasterData = () => {
  return useMutation(async (body: any) => {
    return await MDMService.putMTOAddBufferMaster(body);
  })
}

export const usePutMtoPoogiMasterData = ()=>{
  return useMutation(async (body: any)=>{
    return await MDMService.putMTOAddPoogiMaster(body);
  })
}
export const usePutMtoCCRMasterData = () => {
  return useMutation(async (body: any) => {
    return await MDMService.putMTOAddCCRMaster(body);
  })
}

export const usePutMtoCalendarMasterData = () => {
  return useMutation(async (body:any)=>{
    return await MDMService.putMTOAddCalendarMaster(body)
  })
}

export const useGetBufferMasterData = () => {
  return useMutation(async (body:any) => {
    return await MDMService.getBufferMasterData(body)
  })
}

export const useGetBufferTypeMaster = () => {
  return useMutation(async () => {
    return await MDMService.getBufferTypeMaster()
  })
}

export const useGetMTODrafts = () => {
  return useMutation(async (uid: any) => {
    return await MDMService.getMTODrafts(uid);
  })
}

export const useGetMTODraftById = () => {
  return useMutation(async (props:any) => {
    return await MDMService.getMTODraftById(props.draftId, props.mid);
  })
}

export const useGetCCRMasterData = ()=>{
  return useMutation(async (body:any)=>{
    return await MDMService.getCCRMasterData(body);
  })
}
export const useGetPOOGIMasterData = ()=>{
  return useMutation(async (body:any)=>{
    return await MDMService.getPOOGIMasterData(body);
  })
}

export const useGetCalendarMasterData = ()=>{
  return useMutation(async ()=>{
    return await MDMService.getCalendarMasterData();
  })
}

export const useGetAllUsers = ()=>{
  return useMutation(async ()=>{
    return await MDMService.getAllUsers();
  })
}

export const useGetMaxFolDate = () => {
  return useMutation(async () => {
    return await MDMService.getMaxFolDate()
  })
}

export const useGetApproverName = () => { 
  return useMutation(
    async (params: { approver_ids: any[] }) => {
      return await MDMService.getApproverNames(params);
    }
  );
};
