import {useState, useEffect, useRef, useMemo} from 'react';
import { useNavigate } from "react-router";
import { type Option, type Field,type GetMasterDataPayload, type GridRef, type QueryFilteredDataConfigs, type MDMMasterState } from "../../../../types/MDM";
import {generateOptions, areMasterFiltersValid, parseExcelData, mapStateFiltersToPayload, mapMasterToMasterState, generateSesonalityChartData, checkError,getActionId, mapMasterToColumnDefs,createConflictRowData, createErrorRowData, MainMenuItemsCustomization } from "../../../../../helpers/utils";
import { useGetMasterData, useGetMasterUIConfiguration, useGetCount, useCreateDraft, useModifyDraft, useGetSeasonalityDetails, useModifyMasterData,useModifyMasterDataRetail, useDeleteDraft, useDeleteTask, useValidateMaster, useGetRetailCount,useGetMasterDataRetail, useGetUploadProgress } from "../../../../Services/MTA/MDM";
import { useSelector, useDispatch } from 'react-redux';
import { FILL_MASTERS, FILL_OPTIONS, TOGGLE_SELECT_MASTER_SCREEN, UPDATE_ACTIVE_MASTER, UPDATE_COLDEFS,STORE_ALL_MASTERS, REMOVE_MASTER, ADD_FILTER, REMOVE_FILTER, SYNC_ACTIVE_MASTER_TO_MASTER, UPDATE_ROW_DATA, UPDATE_PROGRESS_STATE, ADD_COLDEFS, REMOVE_ROW_DATA, REMOVE_COLDEFS, SET_DRAFT_ID, TOGGLE_UPLOAD_MODAL, REMOVE_ALL_FILTERS, SET_RECORD_COUNT, UPDATE_DATA_AVAILABILITY_STATUS, RESET_FILTERS, UPDATE_IS_SAVING_DRAFT, ADD_MASTER} from '../../../../../redux/actions/MDM';
import type { RootState } from '../../../../../redux/store/store';
import { notifyError, notifyLoader, notifyPromise, notifySuccess } from '../../../../../helpers/notify';
import ErrorCell from '../../../../../components/VectorFLOW/commons/ErrorCell';
import { AgGridReactProps } from 'ag-grid-react';
import { ColDef, SideBarDef } from 'ag-grid-enterprise';

import WarningCell from '../../../../../components/VectorFLOW/commons/WarningCell';
import { SeasonalityColorCellRenderer, SeasonalityGraphCellRenderer } from '../../../../../components/VectorFLOW/commons/SeasonalityCellRenderers';
import _ from 'lodash';
import { toast } from 'react-toastify';
import ConflictErrorCellRenderer from './ConflictErrorCellRenderer';
import { v4 as uuidv4 } from 'uuid';
import VFLoader from '../../../../../components/VectorFLOW/commons/VFLoader';

const useViewModify = (pageType:string) => {

    const dispatch = useDispatch();
    const navigate = useNavigate();

    const options = useSelector((state: RootState) => state.mdm.options);
    const selectedOptions = useSelector((state: RootState) => state.mdm.selectedOptions);
    const activeMaster = useSelector((state:RootState) => state.mdm.activeMaster);
    const masters = useSelector((state:RootState)=>state.mdm.masters);

    const [canToggleMaster,setCanToggleMaster] = useState<boolean>(true)

    const isSelectMasterOpen = useSelector((state:RootState) => state.mdm.isSelectMasterOpen);
    const isUploadModalOpen = useSelector((state:RootState)=>state.mdm.isUploadModalOpen)
    const draftID = useSelector((state:RootState) => state.mdm.draftId);
    const chunkSize = useSelector((state:RootState) => state.mdm.chunkSize)
    const recordCount = useSelector((state:RootState) => state.mdm.recordCount)
    const isDataAvailableLocally = useSelector((state:RootState) => state.mdm.isDataAvailableLocally)
    const isSavingToDraft = useSelector((state:RootState) => state.mdm.isSavingToDraft)

    const draftId = useSelector((state:RootState) => state.mdm.draftId)

    const [tempRecordCount,setTempRecordCount] = useState<number>(0)

    const [allMastersState,setAllMasterState] = useState<MDMMasterState[]>([])
    const [isWarningModalOpen,toggleWarningModal] = useState<boolean>(false)
    const [isShowAll,setIsShowAll]=useState<boolean>(true)
    const [isOverlayVisible,setIsOverlayVisible] = useState<boolean>(false)
    // const [isUploadModalOpen,toggleUploadModal] = useState<boolean>(false) 
    // const [recordCount,setRecordCount] = useState<number>(0)
    const [downloadFileName,setDownloadFileName] = useState('');
    const [file,setFile] = useState<File>();
    const [isTableDataLoading,setIsTableDataLoading] = useState<boolean>(false);
    const [defaultToolPanel,setDefaultToolPanel] = useState<string>('');
    const [downloadData,setDownloadData] = useState<boolean>(false);
    const [tempDownloadData,setTempDownloadData] = useState<boolean>(false);
    const [errorDownloadPrefix,setErrorDownloadPrefix] = useState<string>('')
    const [colDefs,setColDefs] = useState<ColDef[]>([]); 
    const [isUploadButtonDisabled,setIsUploadButtonDisabled] = useState<boolean>(true);
    const [chartData,setChartData] = useState<object>();
    const [isSeasonalityChartModalOpen,toggleSeasonalityChartModal] = useState<boolean>(false);
    const [normChangeData,setNormChangeData] = useState<any>([]);
    const [enableEditOnlineReset,setEnableEditOnlineReset] = useState<boolean>(false)

    const [conflictCount,setConflictCount] = useState<number>(0);
    const [errorCount,setErrorCount] = useState<number>(0);
    const [conflictData,setConflictData] = useState<Array<any>>([]);
    const [errorData,setErrorData] = useState<Array<any>>([]);
    const [submittedDataCount,setSubmittedDataCount] = useState<number>(0)
    const [isConflictModalOpen,setIsConflictModalOpen] = useState<boolean>(false)

    const [editOnline,toggleEditOnline] = useState(false);
    const [selectedRowsCount,setSelectedRowsCount] = useState(0);
    const [currentPage,setCurrentPage] = useState(1);
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const VIEWRECORD_PAGE = EnvConfig['VIEWRECORD_PAGE'];  
    const ADDRECORD_PAGE = EnvConfig['ADDRECORD_PAGE'];  
    const DELETERECORD_PAGE = EnvConfig['DELETERECORD_PAGE'];  
    const rowsPerPage = useMemo(()=>{
      if(pageType === 'add') return parseInt(ADDRECORD_PAGE || '50')
      else if(pageType === 'remove') return parseInt(DELETERECORD_PAGE || '50');
      else return parseInt(VIEWRECORD_PAGE || '50');
    },[]);
    const [isSubmitDisabled,setIsSubmitDisabled] = useState(false);

    const [seasonalityActiveQuickFilter,setSeasonalityActiveQuickFilter]  = useState<Array<Array<number>>>([])
    const ref = useRef<GridRef>();
    const tempRef = useRef<GridRef>(); //used for second ag grid instance which is hidden.
    const [tempGridData,setTempGridData] = useState<object[]>([]);

    const [filterButtonStatus,setFilterButtonStatus] = useState<Array<number>>([]);
    const [seasonalityRowData,setSeasonalityRowData] = useState<any>([]);

    const {mutateAsync:masterUIConfiguration,isLoading} = useGetMasterUIConfiguration();

    const [TASK_ID,setTaskId] = useState<string>('');

    const [uploadProgress,setUploadProgress] = useState('');

    const [totalProgress,setTotalProgress] = useState('');
    
    const [WarningFlag,setWarningFlag]=useState(false)


    // const [isDataAvailableLocally,setIsDataAvailableLocally] = useState(false);
   
    // const allMasters:Master[] = masterUIConfiguration?.data.data || [];

    // const allMastersState:MDMMasterState[] = mapMasterToMasterState(allMasters);

    const {mutateAsync:getSeasonalityDetails} = useGetSeasonalityDetails();

    const {mutateAsync:getMasterData} = useGetMasterData();

    const {mutateAsync:getMasterDataRetail} = useGetMasterDataRetail();
    
    const {mutateAsync:getCount} = useGetCount();

    const {mutateAsync:getRetailCount} = useGetRetailCount();

    const {mutateAsync:createDraft} = useCreateDraft()

    const {mutateAsync:modifyDraft} = useModifyDraft();

    const {mutateAsync:deleteDraft} = useDeleteDraft()

    const {mutateAsync:modifyMaster} = useModifyMasterData();

    const {mutateAsync:modifyMasterRetail} = useModifyMasterDataRetail();

    const {mutateAsync:deleteTask} = useDeleteTask();

    const {mutateAsync:validateMaster} = useValidateMaster();

    const {mutateAsync:getUploadProgress} = useGetUploadProgress();

    const validStopStatuses = [1,2,3,4,5,6,21];

    const validResumeStatuses = [23];

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
        pinned:'left',
        cellStyle:{
          overflow:'visible',
          'min-width':180,
        }
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
        pinned:'left',
        cellStyle:{
          overflow:'visible',
          'min-width':180,
        }
      }
  ];

    const onColumnChange = () => {
      const localColDefs = ref.current?.api.getColumnDefs()

      if (ref.current && localColDefs) {
        dispatch(UPDATE_COLDEFS(localColDefs))
        dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
        setDefaultToolPanel(ref.current?.api.isToolPanelShowing() ? 'columns' : '');
      }

    }

    const customCellRenderers = useMemo(() => ({
      loadingOverlay:VFLoader,
      errorCell: ErrorCell,
      warningCell: WarningCell,
      seasonalityColorCellRenderer:SeasonalityColorCellRenderer,
      seasonalityGraphCellRenderer:SeasonalityGraphCellRenderer,
      conflictErrorCellRenderer:ConflictErrorCellRenderer
    }), []);


  
  
    useEffect(()=>{
        
        setColDefs(activeMaster.colDefs);

        if(filterButtonStatus.length !== 0) return;

        if(activeMaster.id === 0){
          if(!isLoading){
            const allOptions:Option[] =  generateOptions(allMastersState);
            dispatch(STORE_ALL_MASTERS(allMastersState));
            dispatch(FILL_OPTIONS(allOptions));
          }
  
          const temp:MDMMasterState[]=[];
          if(selectedOptions.length > 0 && pageType==="modify") dispatch(FILL_MASTERS([...getSelectedMasters(temp)]));
        }
        // if(isToolPanelOpen) ref.current?.api.openToolPanel('columns');

      },[selectedOptions,isLoading,activeMaster,allMastersState]);  

      useEffect(()=>{
        if(masters.length > 0 && filterButtonStatus.length !== 0){
          setFilterButtonStatus(masters.map((master:MDMMasterState)=>master.id));
        }
      },[masters])

      useEffect(()=>{
        
        // if(activeMaster.progress === 'editOnlineSaved'){
        //   //remove Editable Coldefs
        //   const updatedColdefs = activeMaster.colDefs.map((col:ColDef)=>{
        //     return {...col,editable:false}
        //   })
        //   dispatch(UPDATE_COLDEFS(updatedColdefs));
        //   dispatch(REMOVE_COLDEFS(['error','warning']))
        // }


        if(activeMaster.progress === 'editOnline'){
          return onEditOnline('editOnline');
        }
        if(activeMaster.progress === 'deleteOnline'){
          return onEditOnline('deleteOnline');
        }
      },[activeMaster.progress]);

      useEffect(()=>{
        //Effect to Add chart handler when seasonality master
        if(activeMaster.id === 10)
        dispatch(UPDATE_COLDEFS(mapMasterToColumnDefs(activeMaster.fields,activeMaster.id,onShowChart)))

      },[])

      function getSelectedMasterValues() {
        const currentUrl = window.location.href;
        const paramName = 'selectedMaster';
        const regex = new RegExp(`[?&]${paramName}=([^&]*)`);
        const match = currentUrl.match(regex);
    
        if (match) {
            return match[1].split(',');
        }
        
        return [];
    }
      useEffect(()=>{
        const getMasterUIConfigurationData = async()=>{
          const {data} = await masterUIConfiguration(pageType);

          const allMasterData = mapMasterToMasterState(data.data,onShowChart,pageType)
          
          setAllMasterState(allMasterData)
          
          const allOptions:Option[] =  generateOptions(allMasterData);
          dispatch(FILL_OPTIONS(allOptions));
          
        const masterIdsArray = getSelectedMasterValues();
        
          if(masterIdsArray.length > 0 ){
            if(masters?.length)return;
            const matchedItems = allMasterData.filter((item:any) => masterIdsArray.includes(String(item.id)));
            if (matchedItems.length != masterIdsArray.length) {
               window.location.href = "/mta/master-data-management/control-panel";
          }
          
            matchedItems.forEach((item:any)=>{
              dispatch(ADD_MASTER(item))
            })            
            const currentUrl = window.location.href;
            if(currentUrl.includes('&isModalOpen=true')){
            dispatch(UPDATE_ACTIVE_MASTER(0));
            dispatch(TOGGLE_SELECT_MASTER_SCREEN(false));}
          }
         }
         getMasterUIConfigurationData()
      },[])

      useEffect(()=>{
        if(activeMaster.progress==='default' && pageType==='add'){
          dispatch(TOGGLE_UPLOAD_MODAL(true))
        }
      },[activeMaster])

      const SIDEBAR_CONFIG = {
        allowedProgressStates: new Set(['deleteView', 'default', 'view']),
        excludedMasterNames: new Set([
          "ForceNormChange",
          "MOQ",
          "SOB",
         "StopPIPO",
          "SeasonalityStatus"
        ]),
      };

     const isProgressStateValid = SIDEBAR_CONFIG.allowedProgressStates.has(activeMaster?.progress);
     const isMasterNameAllowed = !SIDEBAR_CONFIG.excludedMasterNames.has(activeMaster?.name);
     const shouldShowSidebar = isProgressStateValid && isMasterNameAllowed;

    const sideBar:SideBarDef = {
      toolPanels: [
        {
          id: "columns",
          labelDefault: "Columns",
          labelKey: "columns",
          iconKey: "columns",
          toolPanel: "agColumnsToolPanel",
          toolPanelParams: {
            suppressPivots: true,
            suppressPivotMode: true,
            suppressRowGroups: true,
            suppressValues: true,
          },
        
        },
      ],
      defaultToolPanel:defaultToolPanel,
    }
    const agGridProps:AgGridReactProps = {
      tooltipShowDelay:0,
      readOnlyEdit:true,
      tooltipTrigger:'hover',
      sideBar: shouldShowSidebar ? sideBar : {}, 
     // sideBar:['default','view','deleteView'].includes(activeMaster.progress) ? sideBar : {},
      getMainMenuItems: MainMenuItemsCustomization,
      gridOptions:{
        getRowStyle: (params: any) => {
          if (params.node.rowIndex % 2 === 0) {
            return { background: "#EBEBEB" };
          }
          return { background: "#F7F7F7" };
        },
      },
      pagination:true,
      paginationPageSize:rowsPerPage,
      // suppressPaginationPanel:true,
      onColumnVisible:onColumnChange,
      onToolPanelVisibleChanged:()=>{
        setDefaultToolPanel(ref.current?.api.isToolPanelShowing() ? 'columns' : '');
      },
      // overlayLoadingTemplate:'<object style="position:absolute;top:50%;left:50%;transform:translate(-50%, -50%) scale(2)" type="image/svg+xml" data="/assets/img/VectorFLOW/loaderMedium.svg" aria-label="loading"></object>',
      loadingOverlayComponent:'loadingOverlay',
      onRowDataUpdated:(event:any)=>{
        const downloadableColumnKeys:string[] = [];
        activeMaster.fields.forEach((field:Field)=>{
          if(field.isDownload){
            downloadableColumnKeys.push(field.key)
          }
        });
        
        if(downloadData){
          const currentMaster = masters.find((master:MDMMasterState)=>master.id === activeMaster.id);
          const visibleColumns = ref.current?.api.getAllDisplayedColumns();
          const validColumnKeys:string[] = [];
          if(visibleColumns){
            visibleColumns.forEach((col:any)=>{
              if(isUploadModalOpen && !downloadableColumnKeys.includes(col.colId)){
                return;
              }
              validColumnKeys.push(col.colId)
            })
          }
          if(currentMaster){
            event.api.exportDataAsExcel({fileName:downloadFileName ==='' ? currentMaster.name : downloadFileName,columnKeys: validColumnKeys});
            setDownloadData(false);
          }
        }
      },
   
      rowSelection:'multiple',

      suppressRowClickSelection:true,
      components:customCellRenderers,
      onSelectionChanged:()=>{
        if(ref.current?.api){
          setSelectedRowsCount(ref.current?.api.getSelectedRows().length)
        }
      },
      onGridReady:(params:any)=>{
        if(activeMaster.id==10){         
          params.api.forEachNode((node:any) => {
            const isSelected = node.data.IsSelected === "True";
            node.setSelected(isSelected);
          });       
        }
      },
      onCellEditingStopped(event) {
        const data = event.data;
        const field = event.colDef.field;
        const newValue = event.newValue;
        // const oldRow = activeMaster.rowData.find((row) => row.RN === data.RN);
        if (!field) {
          return;
        }
        // dispatch(REMOVE_COLDEFS(['error','warning']));
        const newRow = { ...data };
        newRow[field] = newValue;
        
        const newRowData = activeMaster.rowData.map((row:any)=>{
          if(JSON.stringify(row) === JSON.stringify(data)){
            let err,warn;
            if(activeMaster.id < 14){
              const {error,warning} = checkError(newRow,activeMaster,pageType);
              err = error;
              warn = warning;

            }
          
            //check if there is any errorenous column
            if(err!==undefined){
              newRow.error = err
            }
            else{
              newRow.error = ""
            }
          
            //check if there is any warning column
            if(warn!==undefined){
              newRow.warning = warn
            }
            else{
              newRow.warning = ""
            }
              return newRow;
        
          }
        
          return row;
        })
       
      
        const ifErrorExists = newRowData.some((row:any)=>("error" in row) && row["error"].length > 0);
        if(ifErrorExists){
           addInvalidDataColDefs('error');
        } else{
          dispatch(REMOVE_COLDEFS(['error']));
        }
        const ifWarningExists = newRowData.some((row:any)=>("warning" in row)&&row["warning"].length > 0);
        if(ifWarningExists){
           addInvalidDataColDefs('warning');
        } else{
          dispatch(REMOVE_COLDEFS(['warning']));
        }
        setEnableEditOnlineReset(true)
        dispatch(UPDATE_ROW_DATA([...newRowData]))
      },
   
    }

    function hasWarning(array: Array<any>): boolean {
      for (let i = 0; i < array.length; i++) {
          const warning = array[i].warning;
          if (warning && warning.length > 0) {
              return true; 
          }
      }
      return false; 
  }
  

    const getTempGridColDefs = () => {
      //check if it already contains
      let doesInvalidColDefExists = false;
      invalidDataColdefs.forEach((invalidColumn:ColDef)=>{
         if(activeMaster.colDefs.find((column:ColDef)=>invalidColumn.colId === column.colId)) doesInvalidColDefExists = true;
      })

      const activeMasterColDefsRequiredCols = activeMaster.colDefs.filter((cols)=> cols.colId !== "checkbox")
      if(doesInvalidColDefExists){
       return [...activeMasterColDefsRequiredCols]
      }
       
      if (activeMaster.name === 'SKULocation') {
        if(WarningFlag){
          return [...invalidDataColdefs.filter(colDef => colDef.field === 'error' || colDef.field === 'warning'), ...activeMasterColDefsRequiredCols];
        }else{
          return [...invalidDataColdefs.filter(colDef => colDef.field === 'error'), ...activeMasterColDefsRequiredCols];
        }
    } else {
        return [...invalidDataColdefs.filter(colDef => colDef.field === 'error'), ...activeMasterColDefsRequiredCols];
    }
}

    const tempAgGridProps:AgGridReactProps = {
      columnDefs:getTempGridColDefs(),
      onRowDataUpdated:(event)=>{
        if(tempDownloadData) event.api.exportDataAsExcel({fileName:downloadFileName ? `${errorDownloadPrefix}Error-` + downloadFileName : `${errorDownloadPrefix}Error-`+ activeMaster.name});
      }
    };


    const addCheckBoxColDefs = () => {
      // if(activeMaster.rowData.length===0){
      //   return
      // }
      const checkboxColDefs:ColDef[] = [
        {
          field:'checkbox',
          colId:'checkbox',
          headerName:'',
          width:70,
          checkboxSelection:true,
          headerCheckboxSelection:true,
          headerCheckboxSelectionCurrentPageOnly:true,
          resizable:false,
          suppressMenu: true,
          maxWidth: 40,
          pinned: 'left',
          filter: false
        },
      ]
      dispatch(ADD_COLDEFS({colDefs:checkboxColDefs}));
      dispatch(SYNC_ACTIVE_MASTER_TO_MASTER())
    }

  

    const addInvalidDataColDefs = (columnName: string) => {
      // Check if the column already exists
      const columnAlreadyExists = colDefs.some((colDef: ColDef) => colDef.colId === columnName);

      if (!columnAlreadyExists) {       
        dispatch(ADD_COLDEFS({colDefs:[columnName === 'error' ? invalidDataColdefs[1] : invalidDataColdefs[0]]}));
      } else {
        console.log(`${columnName} column already exists`);
      }
    }

    // const addInvalidDataColDefs = (columnName:string) => {
    //   dispatch(ADD_COLDEFS({colDefs:[columnName === 'error' ? invalidDataColdefs[1] : invalidDataColdefs[0]]}));
    //   // dispatch(SYNC_ACTIVE_MASTER_TO_MASTER())
    // }

    const getCurrentVisbileColumns = () => {
      const columnData = ref.current?.api.getAllDisplayedColumns();
      return columnData?.map((column:any) => ({key:column.colDef.field}));
    }

    const getAllVisibleColums =()=>{
      const columnData=ref.current?.api.getAllGridColumns();
      return columnData?.map((column:any)=>({key:column.colDef.field}))
    }

    const queryFilteredData = async (configs:QueryFilteredDataConfigs) => {
      const {filters,pagination,fields,count,currentPage,rowsPerPage} = configs;
      const payload:GetMasterDataPayload = {
        id:activeMaster.id,
        name:activeMaster.name,
        filters:filters,
        fields:fields,
      }

      if(pagination && !count) {
        payload.paginationParameter = {
          pageNumber:currentPage,
          recordsPerPage:rowsPerPage
        }
      }
      let resultData;
      if(count){
        if(activeMaster.id > 14){
          resultData =  await getRetailCount(payload);
        }
        else{
          resultData =  await getCount(payload);
        }
      }
      else{
        if(activeMaster.id > 14){
          resultData = await getMasterDataRetail(payload); 
        }
        else{
          resultData = await getMasterData(payload); 
        }
      }

      return resultData;
    }

    const queryAllData = async (configs:QueryFilteredDataConfigs) => {
      const {pagination,fields,count,currentPage,rowsPerPage} = configs;
      const payload:GetMasterDataPayload = {
        id:activeMaster.id,
        name:activeMaster.name,
        filters:[],
        fields:fields,
      }

      if(pagination && !count) {
        payload.paginationParameter = {
          pageNumber:currentPage,
          recordsPerPage:rowsPerPage
        }
      }
      let resultData;
      if(count){
        if(activeMaster.id > 14){
          resultData =  await getRetailCount(payload);
        }
        else{
          resultData =  await getCount(payload);
        }
      }
      else{
        if(activeMaster.id > 14){
          resultData = await getMasterDataRetail(payload); 
        }
        else{
          resultData = await getMasterData(payload); 
        }
      }

      return resultData;
    }

    const getSelectedMasters = (temp:MDMMasterState[]) => {
        selectedOptions.forEach((selectedOption:Option)=>{
          allMastersState.forEach((master:MDMMasterState)=>{
            if(master.fields.find((field:Field)=>field.displayName === selectedOption.label) && !temp.find((selectedMaster:MDMMasterState)=>selectedMaster.id === master.id)) temp.push(master);
          })
        });
        return temp;
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
    const handleSelectMasterSubmit = () => {
      updateUrlIsModalOpen();
      masters.forEach((master:MDMMasterState)=>{
        if(!master.isChecked){
          dispatch(REMOVE_MASTER(master.id));
        }
      })
      // if(activeMaster.id===0){
        // dispatch(UPDATE_ACTIVE_MASTER(0));
        const firstDefaultIndex = masters.findIndex(
          (item) => item.progress !== 'submitted'
        );   
        if (firstDefaultIndex !== -1) {
          dispatch(UPDATE_ACTIVE_MASTER(firstDefaultIndex));
        }
      // }
      // else{
      //   dispatch(UPDATE_ACTIVE_MASTER(masters[0]))
      // }
      dispatch(TOGGLE_SELECT_MASTER_SCREEN(false));
    }

    const handleTabChange = (currMaster: MDMMasterState) => {
      if(currMaster.progress === 'submitted') return notifyError(`The ${currMaster.name} is already submitted`);

      const nextMasterIndex = masters.findIndex((master:MDMMasterState)=>(master.progress !== 'submitted' && master.progress !=='editOnlineSubmitted' && master.progress !=='deleteOnlineSubmitted'));

      if(currMaster.id === masters[nextMasterIndex].id) return dispatch(UPDATE_ACTIVE_MASTER(nextMasterIndex));
      else return notifyError(`Please Complete the ${masters[nextMasterIndex].name}`);  

      
      
    }

    const generateDraftPayload = (rowData:any,draftId?:string)=>{
      const pathName = window.location.pathname.split('/')
      const instanceName = activeMaster
      ? activeMaster.id == 12
          ? 'DeltaPercentageSeasonality'
          : activeMaster.id == 11
          ? 'AbsoluteValueSeasonality'
          : activeMaster?.name || ''
      : '';      
      // masters.map((master:MDMMasterState)=>{
      //   instanceName += ` ${master.name}`
      // })
      return{
        instanceName:instanceName,
        searchKey:instanceName, 
        actionType:getActionId(pathName[pathName.length-1]).id,
        draftId:draftId,
        // draftData:masters.map((master:MDMMasterState)=>{
 
        //   return {
        //     masterId:master.id,
        //     status:master.progress,
        //     gridState:master.id===activeMaster.id?JSON.stringify(activeMaster.colDefs):'',
        //     dataMaster:master.id===activeMaster.id?rowData:[]
        //   }
        // })
        draftData:[{
          masterId:activeMaster.id,
          status:activeMaster.progress,
          gridState:JSON.stringify(activeMaster.colDefs),
          dataMaster:rowData
      }]
       
        // masters.map((master:MDMMasterState)=>{
 
        //   return {
        //     masterId:master.id,
        //     status:master.progress,
        //     gridState:master.id===activeMaster.id?JSON.stringify(activeMaster.colDefs):'',
        //     dataMaster:master.id===activeMaster.id?rowData:[]
        //   }
        // })
      }
    }
    
    function removeSelectedMasterValue(masterId:any) {
      const currentUrl = window.location.href;
      const paramName = 'selectedMaster';
  
      const regex = new RegExp(`[?&]${paramName}=([^&]*)`);
      const match = currentUrl.match(regex);
  
      if (match) {
          const currentValues = match[1].split(',');

          if (currentValues.length === 1) {
              console.log('Only one value present in selectedMaster. No changes made.');
              return;
          }

          const newValues = currentValues.filter(value => value !== masterId);
  
          const newParamString = newValues.length ? `${paramName}=${newValues.join(',')}` : '';
  
          let newUrl;
          if (newParamString) {
              newUrl = currentUrl.replace(regex, `${match[0][0]}${newParamString}`);
          } else {
              newUrl = currentUrl.replace(regex, '');
              newUrl = newUrl.replace(/[?&]$/, '');
          }
  
          window.history.replaceState(null, '', newUrl);
      } else {
          console.log('No "selectedMaster" parameter found in the URL.');
      }
  }
//   function checkMasterProgress(masterArray: any) {
//     let defaultProgressCount = 0; 
//     for (const master of masterArray) {
//         if (master.progress === "default" || master.progress === "view") {
//             defaultProgressCount++; 
//         }
//     }
//     return defaultProgressCount === 1;
// }

    const handleTabClose = (e:React.MouseEvent<HTMLElement>,currMaster:MDMMasterState) => {
      e.stopPropagation();
      const nonClosableStates = ['default', 'view','phaseInPhaseOut' , 'seasonality', 'deleteView'];
      const incompleteMastersCount = masters.filter((master: MDMMasterState) => master.progress !== 'submitted').length;
      if (incompleteMastersCount === 1 && currMaster.progress !== 'submitted') {
        return notifyError('Cannot close the tab as it is the only incomplete master'); // Notify if this is the only incomplete master
      }
    if (!nonClosableStates.includes(currMaster.progress)) {
      return notifyError(`Please Complete the ${currMaster.name}`);
    }
    if(masters?.length === 1){
      return notifyError("There Should be atleast one selected Master")
    }
    dispatch(REMOVE_MASTER(currMaster.id));
    setDownloadData(false);
    if(currMaster.id === activeMaster.id){
        removeSelectedMasterValue(String(currMaster.id));
        const mastersLength = masters.length
        for (let index = 0; index < mastersLength; index++) {
          
          if(masters[index].progress!=='submitted'){
            dispatch(UPDATE_ACTIVE_MASTER(index))
            return
          }
        }

}
}
    // const handleTabClose = (e:React.MouseEvent<HTMLElement>,currMaster:MDMMasterState) => {
    //   e.stopPropagation();
    //   const incompleteMastersCount = masters.filter((master: MDMMasterState) => 
    //     master.progress !== 'submitted' && master.progress !== 'editOnlineSubmitted'
    //   ).length;
    
    //   if (incompleteMastersCount === 1 && currMaster.progress !== 'submitted' && currMaster.progress !== 'editOnlineSubmitted') {
    //     return notifyError('Cannot close the tab as it is the only incomplete master'); // Notify if this is the only incomplete master
    //   }
    //   if(checkMasterProgress(masters)) {return notifyError(`Please Complete the ${currMaster.name}`)}
    //   const nextMasterIndex = masters?.findIndex((master:MDMMasterState)=>(master.progress !== 'submitted' && master.progress !=='editOnlineSubmitted'));
    //   if(currMaster.id !== masters[nextMasterIndex].id)  return notifyError(`Please Complete the ${masters[nextMasterIndex].name}`);  
    //   if(masters.length === 1){
    //     return notifyError("There Should be atleast one selected Master")
    //   }
    //   dispatch(REMOVE_MASTER(currMaster.id));
    //   setDownloadData(false);
    //   if(currMaster.id === activeMaster.id){
    //       removeSelectedMasterValue(String(currMaster.id));
    //       const mastersLength = masters.length
    //       for (let index = 0; index < mastersLength; index++) {
            
    //         if(masters[index].progress!=='submitted'){
    //           dispatch(UPDATE_ACTIVE_MASTER(index))
    //           return
    //         }
    //       }
        
    //     }
    //   }
    

      
    const addNewMaster = ()=>{
      if(allMastersState.length === masters.length) {
        notifyError('All Masters have already been selected. Cannot add more masters');
        return;
      }
      setCanToggleMaster(false)
      dispatch(TOGGLE_SELECT_MASTER_SCREEN(true));
      setDownloadData(false);
      setTempDownloadData(false);
    }

    const handleOnAddFilter = ()=>{
      dispatch(ADD_FILTER());
      dispatch(SYNC_ACTIVE_MASTER_TO_MASTER())
    }
  
    const handleOnDeleteFilter = (id:string)=>{
     
      if (activeMaster.filters.length === 1) {
        
        dispatch(RESET_FILTERS());
        dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
      
        return;
      }
      dispatch(REMOVE_FILTER(id));
      dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
    }

    const handleApplyFilter =async (showAll?:boolean) => {
     if(showAll) setIsShowAll(showAll)
     else setIsShowAll(false)
      if(downloadData) setDownloadData(false)
      const currMasterFilters = activeMaster.filters;
      if(!areMasterFiltersValid(currMasterFilters) && !showAll){
        return notifyError('Filter cannot be empty')
      }

      const payloadFilters = mapStateFiltersToPayload(currMasterFilters);
      const payloadFields:any = getCurrentVisbileColumns();

      setIsTableDataLoading(true);

      let result;
      if(showAll){
        result = await queryAllData({filters:payloadFilters,fields:payloadFields,pagination:false,count:true,rowsPerPage});
      }
      else{
        result = await queryFilteredData({filters:payloadFilters,fields:payloadFields,pagination:false,count:true,rowsPerPage});
      }

      setIsTableDataLoading(false);
      // if(!result.data.recordCount || result.data.recordCount==0 || result.data.recordCount=='')dispatch(SET_RECORD_COUNT(0))
      // else{
      //   dispatch(SET_RECORD_COUNT(result.data.recordCount))
      // }
      if(!result.data.recordCount || result.data.recordCount==0 || result.data.recordCount=='')setTempRecordCount(0)
      else{
        setTempRecordCount(result.data.recordCount)
      }
      // if(result.data.recordCount<=rowsPerPage){
      //   dispatch(UPDATE_DATA_AVAILABILITY_STATUS(true))
      // }
      // else{
      //   dispatch(UPDATE_DATA_AVAILABILITY_STATUS(false))
      // }

      toggleWarningModal(true);    
      setCurrentPage(1);
      if(activeMaster.id == 10) setSeasonalityActiveQuickFilter([])
    }

    const onWarningModalClose = ()=>{
      // dispatch(UPDATE_ROW_DATA([]));
      toggleWarningModal(false);
      setIsTableDataLoading(false);
      setTempRecordCount(0)
    }

    const onWarningModalSuccess = async (refetch?:boolean)=>{
     
      refetch = refetch?refetch:false

      const currMasterFilters = activeMaster.filters;

      const payloadFilters = mapStateFiltersToPayload(currMasterFilters);
      let payloadFields:any = getCurrentVisbileColumns();
      payloadFields = payloadFields.filter((field:any)=>!['checkbox','graph','color'].includes(field.key))
      
      setIsTableDataLoading(true);
      let result:any;

      if((!areMasterFiltersValid(currMasterFilters) && activeMaster.filters.length === 1) || isShowAll){
        if(activeMaster.id==10 || activeMaster.id==6){
          result = await notifyPromise(queryAllData({filters:payloadFilters,fields:payloadFields,pagination:false}),{
            success:"Data Fetched Successfully",
            error:"Something Went Wrong",
            pending:"Loading Data"
          });
          dispatch(UPDATE_DATA_AVAILABILITY_STATUS(true));
        }
        else{
          result = await notifyPromise(queryAllData({filters:payloadFilters,fields:payloadFields,pagination:true,currentPage:1,rowsPerPage}),{
            success:"Data Fetched Successfully",
            error:"Something Went Wrong",
            pending:"Loading Data"
          }); 
      }
      dispatch(RESET_FILTERS())
    }
      else{
        if(activeMaster.id==10 || activeMaster.id==6){
          result = await notifyPromise(queryFilteredData({filters:payloadFilters,fields:payloadFields,pagination:false}),{
            success:"Data Fetched Successfully",
            error:"Something Went Wrong",
            pending:"Loading Data"
          }); 
          dispatch(UPDATE_DATA_AVAILABILITY_STATUS(true));
        }
        else{
          result = await notifyPromise(queryFilteredData({filters:payloadFilters,fields:payloadFields,pagination:true,currentPage:1,rowsPerPage}),{
            success:"Data Fetched Successfully",
            error:"Something Went Wrong",
            pending:"Loading Data"
          }); 
      }
     
      }
      

      if(tempRecordCount<=rowsPerPage){
        dispatch(UPDATE_DATA_AVAILABILITY_STATUS(true))
      }
      else{
        dispatch(UPDATE_DATA_AVAILABILITY_STATUS(false))
      }
      
      if(tempRecordCount <= rowsPerPage){
        toggleEditOnline(true);
      }
      else{
        toggleEditOnline(false);
      }

      
        setIsTableDataLoading(false);
        if(tempRecordCount == 0){
          toggleWarningModal(false);
          return;
        }
        
        const tempRowData = result?.data?.data?.map((row:any)=>{
          const newRow = {...row};
          
          Object.keys(newRow).map((key)=>{
            const currentColDef = activeMaster.colDefs.find((c)=>c.colId===key)
            const cellDataType = currentColDef?.cellDataType
            if(cellDataType==='number' && newRow[key]!== null){
              if(isNaN(parseFloat(newRow[key]))){
                newRow[key]='';
              }else{
                newRow[key] = parseFloat(newRow[key])
              }
            }
          })

          return newRow
        })

        dispatch(UPDATE_ROW_DATA(tempRowData));
        if(refetch)return
        toggleWarningModal(false);
        if(pageType==='remove'){
           dispatch(UPDATE_PROGRESS_STATE('deleteView'));
        }
        else{
          if(activeMaster.id==10){
            dispatch(UPDATE_PROGRESS_STATE('seasonality'));
            return  dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
          }
          if(activeMaster.id==6){
             dispatch(UPDATE_PROGRESS_STATE('phaseInPhaseOut')); 
          }
          else  dispatch(UPDATE_PROGRESS_STATE('view')); 
        }
        dispatch(SET_RECORD_COUNT(tempRecordCount))
        dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
    }

    const onEditOnline = (progress:any) => {

      const updatedColdefs = activeMaster.colDefs.map((col:ColDef)=>{
        const isEditable = activeMaster.fields.find((field:Field)=>field.key === col.colId )?.isEdit;
        
        if(isEditable){
          return {...col,editable:true}
        } 
        return {...col}
      })

      dispatch(UPDATE_PROGRESS_STATE(progress))
      dispatch(UPDATE_COLDEFS(updatedColdefs))
      dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());

    }

    const resetColumnEditing = () => {
      toggleEditOnline(false);
      const updatedColdefs = activeMaster.colDefs.map((col:ColDef)=>{
          return {...col,editable:false}
      })
      dispatch(UPDATE_COLDEFS(updatedColdefs))
    };


      const onUploadMaster = async (RECORD_UPLOAD_LIMIT:any) => {
        // let intervalID:any;
        try {
          if(!file){
            notifyError('Please select a file to upload.');
            return
          }
          const selectedColumns = ref.current?.api.getAllDisplayedColumns();
          // const toasId = notifyLoader("Reading File");
          setIsOverlayVisible(true)
  
          if(activeMaster.id < 14){
            await parseExcelData(file,activeMaster,pageType,selectedColumns,RECORD_UPLOAD_LIMIT);
          }
          
          const formData = new FormData();
          formData.append("file", file);
          formData.append("ui_config",JSON.stringify(activeMaster.fields))
          formData.append("screen_type",JSON.stringify({screenType:pageType}))
          const processId = uuidv4();
          
          formData.append("process_id",JSON.stringify({processId:processId}));

          // intervalID = setInterval(async ()=>{
          //   const progress = await getUploadProgress(processId);
          //   if(progress.data!==undefined){
          //     setUploadProgress(progress.data.progress);
          //     setTotalProgress(progress.data.totalRows)
          //   }
          // },1000)

          const response = await validateMaster({formData,masterId:activeMaster.id});
          // clearInterval(intervalID);
          let result = JSON.parse(response.data)
          const errorAndWarningData = result.filter((data:any)=>data.error.length > 0 || data.warning.length > 0 )
          result = [...errorAndWarningData,... result.filter((data:any)=>data.error.length === 0 && data.warning.length === 0 )]
          

          const ifErrorExists = result.find((data:any)=>data.error.length > 1);
          const ifWarningExists = result.find((data:any)=>data.warning.length > 1);

          if(ifErrorExists) {
            dispatch(UPDATE_PROGRESS_STATE('error'));
             if(!activeMaster.colDefs.some((colDef:ColDef)=>colDef.colId === "error")){
              addInvalidDataColDefs('error');
            }
          }
          if(ifWarningExists){
            // dispatch(UPDATE_PROGRESS_STATE('error'));
            addInvalidDataColDefs('warning');
          }
          if(!ifErrorExists){
            if(activeMaster.progress==='deleteView') dispatch(UPDATE_PROGRESS_STATE('deleteUploaded'));
            else  dispatch(UPDATE_PROGRESS_STATE('uploaded'));
            addCheckBoxColDefs();
           }

          dispatch(SET_RECORD_COUNT(result.length));
          dispatch(UPDATE_DATA_AVAILABILITY_STATUS(true));
          dispatch(UPDATE_ROW_DATA(result));
          dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
          dispatch(TOGGLE_UPLOAD_MODAL(false));
          setIsOverlayVisible(false);
          setIsOverlayVisible(false)
          notifySuccess(`Data Uploaded Successfully`);
          setDownloadData(false);
          setTempDownloadData(false);
          setCurrentPage(1);
          setFile(undefined)
          }
         catch (error:any) {
          toast.dismiss();
          console.error(error)
          notifyError(error.message);
          setIsOverlayVisible(false);
          // if(intervalID) clearInterval(intervalID);
        }

      }

      const exportToExcel = async (fromUploadModal?:boolean)=>{
        try {
          const currMasterFilters = activeMaster.filters;
          const payloadFilters = areMasterFiltersValid(currMasterFilters)? mapStateFiltersToPayload(currMasterFilters) : [];
        
          const payloadFields:any = getCurrentVisbileColumns();
          
          const numberOfPages = Math.ceil(recordCount/chunkSize);
          const toastId = notifyLoader(`Downloading Data 0 / ${recordCount}`)
          const rows = [];
          for(let i=1; i<=numberOfPages; i++){
            const result = await queryFilteredData({filters:payloadFilters,fields:payloadFields,showAll:false,pagination:true,currentPage:i,rowsPerPage:chunkSize});
            if(result.data.data === null) throw new Error("Something Went Wrong")
            rows.push(...result.data.data)
            if(i===numberOfPages) toast.update(toastId,{render:`Downloading Data ${recordCount} / ${recordCount}`})
            else toast.update(toastId,{render:`Downloading Data ${i*chunkSize} / ${recordCount}`})
          }

          dispatch(UPDATE_ROW_DATA(rows));
          dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
          setDownloadData(true);
          toast.dismiss(toastId);
          if(fromUploadModal){
            setIsUploadButtonDisabled(false);
            notifySuccess(`Data Downloaded Successfully`);
            return
          }

          notifySuccess(`Data Exported Successfully`);
        } catch (error) {
          toast.dismiss();
          notifyError('Something Went Wrong');
        }
        
      }
      const onClearExportError = (source:string) => {
        const erroneusData:any[] = [];
        const validData:any[] = [] 
        activeMaster.rowData.forEach((data:any)=>{
          if(data['warning'] && data['warning'].length>0){
            setWarningFlag(true)
            erroneusData.push(data)
          }

          if (data['error'] && data['error'].length > 0 ) {
            erroneusData.push(data);
          }
          else{
            validData.push(data);
          }
        });
        setTempGridData(erroneusData);
        setTempDownloadData(true);
        setErrorDownloadPrefix(source)

        if((activeMaster.progress!=='submitted') && (activeMaster.progress!=='deleteOnlineSubmitted')){
          dispatch(UPDATE_ROW_DATA(validData));
        
          dispatch(REMOVE_COLDEFS(['error','warning']));
          
          
          if(pageType==='remove') {
            
            if(validData.length===0){
              
              dispatch(UPDATE_PROGRESS_STATE('submitted'))
            }
            else{
            dispatch(UPDATE_PROGRESS_STATE('deleteUploaded'));
            }
          }
          else if(pageType === 'add' || pageType == 'modify'){
            if( validData.length===0){
              dispatch(UPDATE_PROGRESS_STATE('submitted'))
            }
            else{
              dispatch(UPDATE_PROGRESS_STATE('uploaded'));
            }
          }
          // else if(validData.length!==0) dispatch(UPDATE_PROGRESS_STATE('uploaded'));
         else if(validData.length===0){
            if(draftID.length===0){
              dispatch(UPDATE_PROGRESS_STATE('Discard'))
            }else{
              dispatch(UPDATE_PROGRESS_STATE('DiscardDraft'))
            }
          }
          dispatch(SET_RECORD_COUNT(validData.length))
          dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
          if(validData.length!==0){
            addCheckBoxColDefs();
          }
        }
        
      }

      
      const deleteSelected = () => {
        const selectedRows = ref.current?.api.getSelectedRows();
        if(selectedRows && selectedRows.length > 0){
          dispatch(REMOVE_ROW_DATA(selectedRows));
          notifySuccess(`${selectedRows?.length} records deleted successfully`);
          setSelectedRowsCount(0);
          if(recordCount - selectedRows?.length === 0){
            dispatch(UPDATE_PROGRESS_STATE('submitted'));
          }
          dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
          if(recordCount===selectedRows.length){
            if(draftID.length===0){
              dispatch(UPDATE_PROGRESS_STATE('Discard'))
            }else{
              dispatch(UPDATE_PROGRESS_STATE('DiscardDraft'))
            }
          }
          dispatch(SET_RECORD_COUNT(recordCount-selectedRows.length));
        }
        else{
          notifyError("Please Select Rows to Delete");
        }
        
      }

      const handleChangePage = async (pageNo:any) => {

        setCurrentPage(pageNo);
        setIsTableDataLoading(true)
        if(activeMaster.rowData.length > rowsPerPage){
            ref.current?.api.paginationGoToPage(pageNo-1);
            setIsTableDataLoading(false);
            return;
        }
        
        const payloadFilters = mapStateFiltersToPayload(activeMaster.filters);
        const payloadFields:any = getCurrentVisbileColumns();
        let result;
        if(!areMasterFiltersValid(activeMaster.filters) && activeMaster.filters.length === 1){
          result = await queryAllData({filters:payloadFilters,fields:payloadFields,pagination:true,currentPage:pageNo,rowsPerPage});
        }
        else{
          result = await queryFilteredData({filters:payloadFilters,fields:payloadFields,pagination:true,currentPage:pageNo,rowsPerPage});
        }
        
        dispatch(UPDATE_ROW_DATA(result.data.data));
        dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
        setIsTableDataLoading(false);

      }

      const postMasterDataChunks = async (rowData:any,isOverWrite?:boolean,actionStatus="") => {
        const columnsToOmit = activeMaster.fields.filter((field:Field)=>!field.isDownload).map((field:Field)=>field.key)
        if(([6].includes(parseInt(String(activeMaster.id),10)) === false)){
          //CleanUp Row Data
          rowData = rowData.map((row:any)=>_.omit(row,'error','warning','users',columnsToOmit));
        }

        // Convert To String
        rowData = rowData.map((row:any)=>{
          const tempRow:any = {};
          Object.keys(row).forEach((key:string)=>{
            if(row[key]===undefined || row[key]===null){
              tempRow[key] = "";
            }
            else{
              tempRow[key] = row[key].toString();
            }
          })
          return tempRow;
        });
        let taskId:any = '';
        let toastId:any = '';
        let conflictCount = 0;
        let errorCount = 0;
        const tempConflictData:any = [];
        const errorData:any = [];
        try {
          let submitProgress = 0;
          const payload:any = {
            id:activeMaster.id,
            action:actionStatus,
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
              
              if(activeMaster.id > 14){
                data = await modifyMasterRetail(payload);
              }
              else{
                data = await modifyMaster(payload);
                if (data.status !== 200) {
                  throw new Error(`Request failed with status`);
               }
                
                
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

              setTaskId(data.data.taskId);
              
              if(data.data.conflictErrorCount){
                conflictCount += parseInt(data.data.conflictErrorCount,10);
              }
              errorCount += parseInt(data.data.errorCount,10);
              const conflictedRows = data.data.conflictError;
              const errorenousRows = data.data.error;
              
              if(conflictedRows instanceof Array) {
                conflictedRows.forEach((row:any)=>{
                  const userIndex = tempConflictData.findIndex((data:any)=>data.user === row.user);
                  if(userIndex >= 0){
                    tempConflictData[userIndex].conflictdetails = [...tempConflictData[userIndex].conflictdetails,...row.conflictdetails]
                  }
                  else{
                    tempConflictData.push({
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

            const intersectionCount = conflictCount + errorCount - activeMaster.rowData.length
            
            const pureErrorCount = activeMaster.rowData.length + intersectionCount - conflictCount

            const pureConflictCount = activeMaster.rowData.length + intersectionCount - errorCount
            toast.dismiss(toastId);
            setConflictCount(pureConflictCount);
            setErrorCount(pureErrorCount);
            setConflictData(tempConflictData);
            setErrorData(errorData)
            // console.log({isConflicts:pureConflictCount>0,errorCount:pureErrorCount,errorData,conflictCount:pureConflictCount,conflictData} )
            return {isConflicts:pureConflictCount>0,errorCount:pureErrorCount,errorData,conflictCount:pureConflictCount,conflictData:tempConflictData} 
            
          }
         catch (error) {
          notifyError("Something Went Wrong");
          if(taskId.length > 0){
            await deleteTask(taskId);
          }
          toast.dismiss(toastId)
          return {isDisaster:true,isConflicts:true,errorCount,errorData,conflictCount,conflictData} 
        }
      }
          
      const onSubmit = async(isOverWrite?:boolean) => {
        try{
        if(activeMaster.rowData.length === 0) {
          notifyError("No Data to Submit") ;
          return 
        }
        const totalRecords = activeMaster.rowData.length

        if(isSubmitDisabled) return;

        setIsSubmitDisabled(true)
        dispatch(REMOVE_COLDEFS(['checkbox']));

        //check if errorneous Data
        const errorData1 = activeMaster.rowData.find((row:any)=>{
          return (row.error ) &&( row.error!=='' )
        });
        if(errorData1){
          notifyError('Please Clear Errors Before Submitting');
          return;
        }
        

        if(activeMaster.progress === 'editOnline'){
          //remove Editable Coldefs
          const updatedColdefs = activeMaster.colDefs.map((col:ColDef)=>{
            return {...col,editable:false}
          })
          dispatch(UPDATE_COLDEFS(updatedColdefs));
          // dispatch(REMOVE_COLDEFS(['error','warning']))
        }

        
 
        dispatch(SYNC_ACTIVE_MASTER_TO_MASTER())
     
        //let result;
 
        if(activeMaster.progress === 'editOnline'){
          const {isDisaster,isConflicts,errorCount:localErrorCount,errorData:localErrorData,conflictData:localConflictData} = await postMasterDataChunks(activeMaster.rowData,isOverWrite);
          let errorRowData:any[]=[];
          //result = !isConflicts
          if(isDisaster){
            setIsSubmitDisabled(false)
            return 
          } 
          if(!isConflicts){
            if(localErrorCount>0 || errorCount>0){
             
              if(localErrorCount>0){
                errorRowData = createErrorRowData(localErrorData,activeMaster.id)
              }
              else{
                errorRowData = createErrorRowData(errorData,activeMaster.id)
              }
              if(!activeMaster.colDefs.find((c:ColDef)=>c.colId==='error')){
                addInvalidDataColDefs('error')
              }
              if(errorRowData.length>0){
                dispatch(UPDATE_ROW_DATA(errorRowData))
                dispatch(SET_RECORD_COUNT(errorRowData.length))
              }
            }
            setSelectedRowsCount(0);
            sendErrorToastMessage(totalRecords,errorRowData,localConflictData.length,'editOnlineSubmitted')
            // dispatch(UPDATE_PROGRESS_STATE('editOnlineSubmitted'));
            dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
            if(draftID.length > 0){
              await deleteDraft(draftID);
            }
          }
          else{
            // console.time('That took ')
            // console.log('Calculating...')
            const tempCon = createConflictRowData(localConflictData,activeMaster.id)
            const tempError = createErrorRowData(localErrorData,activeMaster.id)
            const tempResult:any = []

            tempCon.forEach((t:any)=>{
              const exist = tempError.find((e:any)=>e.sc===t?.sc)
              if(exist)tempResult.push(exist)
            })
            
            // console.log("Conflicts Count : ",tempCon.length)
            // console.log("Errors Count : ",tempError.length)
            // console.log("Intersection Count : ",tempResult.length)
            // console.log("Not Submitted Count : ",(tempCon.length -tempResult.length )+(tempError.length -tempResult.length ))
            // console.log("Active master length",activeMaster.rowData.length);
            // console.log("Submitted Count : ",activeMaster.rowData.length - ((tempCon.length -tempResult.length )+(tempError.length -tempResult.length )))
            // console.timeEnd('That took ')
            setConflictData(tempCon)
            setConflictCount(tempCon.length)
            setSubmittedDataCount(activeMaster.rowData.length - ((tempCon.length -tempResult.length )+(tempError.length -tempResult.length )))
            setIsConflictModalOpen(true)
            //addCheckBoxColDefs()
            dispatch(UPDATE_PROGRESS_STATE('editOnlineConflicts'))
          }
 
        }
        else{

          const {isDisaster,isConflicts,errorCount:localErrorCount,errorData:localErrorData,conflictData:localConflictData} = await postMasterDataChunks(activeMaster.rowData,isOverWrite);
          let errorRowData:any[]=[];
          if(isDisaster){
            setIsSubmitDisabled(false)
            return 
          } 
         if(!isConflicts){
          if(localErrorCount>0 ){
            
            if(localErrorCount>0){
              errorRowData = createErrorRowData(localErrorData,activeMaster.id)
            }
            else{
              errorRowData = createErrorRowData(errorData,activeMaster.id)
            }

            if(!activeMaster.colDefs.find((c:ColDef)=>c.colId==='error')){
              addInvalidDataColDefs('error')
            }

            if(errorRowData.length>0){
              dispatch(UPDATE_ROW_DATA(errorRowData))
              dispatch(SET_RECORD_COUNT(errorRowData.length))
            }
          }
          

          setSelectedRowsCount(0);
          sendErrorToastMessage(totalRecords,errorRowData,localConflictData.length,'submitted')
          dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());


          if(draftID.length > 0){
            await deleteDraft(draftID);
            dispatch(SET_DRAFT_ID(''));
          }
        }
        else{
          // console.time('That took ')
          // console.log('Calculating...')


          const tempCon = createConflictRowData(localConflictData,activeMaster.id)
          const tempError = createErrorRowData(localErrorData,activeMaster.id)

          const tempResult:any = []

          tempCon.forEach((t:any)=>{
            const exist = tempError.find((e:any)=>e.sc===t?.sc)
            if(exist)tempResult.push(exist)
          })
          
          // console.log("Conflicts Count : ",tempCon.length)
          // console.log("Errors Count : ",tempError.length)
          // console.log("Intersection Count : ",tempResult.length)
          // console.log("Not Submitted Count : ",(tempCon.length -tempResult.length )+(tempError.length -tempResult.length ))
          // console.log("Active master length",activeMaster.rowData.length);
          // console.log("Submitted Count : ",activeMaster.rowData.length - ((tempCon.length -tempResult.length )+(tempError.length -tempResult.length )))
          // console.timeEnd('That took ')
          setConflictData(tempCon)
          setConflictCount(tempCon.length)
          setSubmittedDataCount(activeMaster.rowData.length - ((tempCon.length -tempResult.length )+(tempError.length -tempResult.length )))
          setIsConflictModalOpen(true)
          addCheckBoxColDefs()
          dispatch(UPDATE_PROGRESS_STATE('conflicts'))
        }

        }
      }catch(err){
        notifyError("Something went wrong")
      }finally{
        setIsSubmitDisabled(false)
      }
      }

      const onSeasonalityStatusUpdate = async (status:string) => {
        const selectedRows = ref.current?.api.getSelectedRows();
        if(selectedRows?.length === 0)  {
          notifyError("Please select atleast 1 row");
          return;
        }
        let error = false;

        if(selectedRows){
          if(status === 'stop'){
            for(let i=0; i<selectedRows.length; i++){
              if(selectedRows && !validStopStatuses.includes(selectedRows[i].sts)){
                notifyError('Selected Data Consists some rows that are not eligible for Stopping.')
                error = true;
                break;
              }
            }
          }
          if(status === 'resume'){
            for(let i=0; i<selectedRows.length; i++){
              if(selectedRows && !validResumeStatuses.includes(selectedRows[i].sts)){
                notifyError('Selected Data Consists some rows that are not eligible for Resuming.');
                error = true;
                break;
              }
            }
          }
          if(!error) {
            await postMasterDataChunks(selectedRows,false,status);
            // onWarningModalSuccess(true)
            ref.current?.api.deselectAll();          
            notifySuccess("Status Updated Successfully");
          }
          
        }
       
       

        
      } 


      const sendErrorToastMessage = (totalRecords:any,errorRowData:any,conflictCount:any,state:any) =>{
        const submittedRecordsCount = totalRecords - errorRowData.length - conflictCount

        if(submittedRecordsCount === totalRecords){
          notifySuccess("Modification done Successfully")
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
        else notifySuccess("Modification done Successfully")
        dispatch(UPDATE_PROGRESS_STATE(state));
      }

      const onPIPOStatusUpdate = async () => {
        const selectedRows = ref.current?.api.getSelectedRows();

        if(selectedRows?.length === 0)  {
          notifyError("Please select atleast 1 row");
          return;
        }
        
        await postMasterDataChunks(selectedRows,false,'stop');
        // onWarningModalSuccess(true)
        ref.current?.api.deselectAll()
        notifySuccess("Status Updated Successfully");

      } 

      const onDiscardDraftCallback = async () =>{
        if(draftId.length!==0){
          const toastId = notifyLoader(`Deleting Draft`);
          const result = await deleteDraft(draftID);
          if(result.status===200){
            toast.dismiss(toastId)
            notifySuccess("Deleted Draft")
          }else{
            toast.dismiss(toastId)
            notifyError("Something Went Wrong")
          }
          // dispatch()
          dispatch(UPDATE_PROGRESS_STATE('default'));
          dispatch(UPDATE_ROW_DATA([]));
          dispatch(UPDATE_COLDEFS([]));
          dispatch(REMOVE_ALL_FILTERS());
          dispatch(ADD_FILTER())
          dispatch(SET_DRAFT_ID(''))
          setDownloadData(false);
          setTempDownloadData(false);
          dispatch(FILL_MASTERS([]));
          setFilterButtonStatus([]);
          dispatch(TOGGLE_SELECT_MASTER_SCREEN(true));
          navigate('/mta/master-data-management/saved-drafts')
          return
        }
      }

      function removeModalOpenParameterWithoutReload() {
        const parameterToRemove = '&isModalOpen=true';
        const currentUrl = window.location.href;
      
        // Check if the parameter exists
        if (currentUrl.includes(parameterToRemove)) {
          // Remove the parameter
          const updatedUrl = currentUrl.split(parameterToRemove).join('');
          
          // Update the browser's URL without reloading the page
          window.history.replaceState(null, '', updatedUrl);
        }
      }

      const onBackButton1 = (backUrl?: string) => {
        removeModalOpenParameterWithoutReload()
        setCanToggleMaster(true)
        if(backUrl){
          navigate(backUrl)
        }
        dispatch(UPDATE_PROGRESS_STATE('default'));
        dispatch(UPDATE_ROW_DATA([]));
        dispatch(UPDATE_COLDEFS(activeMaster.colDefs.filter((item: any) => item.field !==  'error')));
        dispatch(REMOVE_ALL_FILTERS());
        dispatch(REMOVE_COLDEFS(['checkbox']));
        dispatch(REMOVE_COLDEFS(['warning']));
        dispatch(REMOVE_COLDEFS(['error']));
        dispatch(ADD_FILTER())
        setDownloadData(false);
        setTempDownloadData(false);
        setFilterButtonStatus([]);
        dispatch(TOGGLE_SELECT_MASTER_SCREEN(true));
        dispatch(SET_DRAFT_ID(''))

        if(pageType==='add')dispatch(TOGGLE_UPLOAD_MODAL(true))
            // dispatch(UPDATE_ACTIVE_MASTER([]))
        // dispatch(UPDATE_COLDEFS([]));
        // dispatch(FILL_MASTERS([]));
        // dispatch(UPDATE_ACTIVE_MASTER({id:0,fields:[],filters:[],progress:'default',name:'',colDefs:[],rowData:[],isChecked:true}))
        
     }

     const onBackButton = (backUrl?: string) => {
      if (activeMaster.progress === 'submitted' || activeMaster.progress === 'editOnlineSubmitted' || activeMaster.progress === 'view' || activeMaster.progress === 'deleteView') {
        // Directly perform the actions without showing the confirmation dialog
        handleBackNavigation(backUrl);
      } else {
        // Show confirmation dialog if current master is incomplete
        const user = confirm("Are you sure you want to go back? All the progress will be lost! Please save to draft.");
        if (user) {
          handleBackNavigation(backUrl);
        }
      }
    };
      

    const handleBackNavigation = (backUrl?: string) =>{
       if(backUrl){
         navigate(backUrl)
       }

       resetColumnEditing()
       toggleEditOnline(false);
       removeModalOpenParameterWithoutReload();
       setCanToggleMaster(true);
      if(activeMaster.progress !== "submitted") { 
        dispatch(UPDATE_PROGRESS_STATE('default')); 
      }
       dispatch(UPDATE_ROW_DATA([]));
       dispatch(UPDATE_COLDEFS(activeMaster.colDefs.filter((item: any) => item.field !== 'error') .map((m: any) => {
        const copy= { ...m };  
        copy.editable = false; 
        return copy;
          })
      ));
      
       dispatch(REMOVE_ALL_FILTERS());
       dispatch(REMOVE_COLDEFS(['checkbox']));
       dispatch(REMOVE_COLDEFS(['warning']));
       dispatch(REMOVE_COLDEFS(['error']));
       dispatch(ADD_FILTER())
       setDownloadData(false);
       setTempDownloadData(false);
       setFilterButtonStatus([]);
       dispatch(TOGGLE_SELECT_MASTER_SCREEN(true));
       dispatch(SET_DRAFT_ID(''))

       if(pageType==='add')dispatch(TOGGLE_UPLOAD_MODAL(false))
       // dispatch(UPDATE_COLDEFS([]));
       // dispatch(UPDATE_ACTIVE_MASTER([]))
      };      
     
    

      const postDraftChunks = async (rowData:any) => {
        let draftId = '';
        let chunkProgress = 0;
        let toastId;

        // Convert To String
        rowData = rowData.map((row:any)=>{
          const tempRow:any = {};
          Object.keys(row).forEach((key:string)=>{
            if(row[key]===undefined || row[key]===null){
              tempRow[key] = "";
            }
            else{
              tempRow[key] = row[key].toString();
            }
          })
          return tempRow;
        });

        try {
          toastId = notifyLoader(`Creating Draft ${chunkProgress}/${activeMaster.rowData.length}`);
          for(let i=0; i < rowData.length; i+=chunkSize){
            if(draftId.length > 0){
              if(i+chunkSize < rowData.length){
                await createDraft(generateDraftPayload(rowData.slice(i,i+chunkSize),draftId));
                toast.update(toastId,{render:`Uploading ${i+chunkSize}/${rowData.length}`})
                chunkProgress+=chunkSize;
              }
              else{
                await createDraft(generateDraftPayload(rowData.slice(i),draftId))
                toast.update(toastId,{render:`Uploading ${rowData.length}/${rowData.length}`})
              }
            }
            else{
              let data:any;
              if(draftID){
                data =  await modifyDraft(generateDraftPayload(rowData.slice(0,chunkSize),draftID));
              }
              else{
                data = await createDraft(generateDraftPayload(rowData.slice(0,chunkSize)));
              }  
              draftId = data.data.data;
              dispatch(SET_DRAFT_ID(data.data.data))
            } 
          }
          toast.dismiss(toastId)
          return true; 
        } catch (error) {
          if(draftId.length > 0 && draftID.length === 0){
            await deleteDraft(draftId)
          }
          toast.dismiss(toastId);
          return false
        }

      }
      const onSaveToDraft = async () => {
        toggleEditOnline(false)
        // resetColumnEditing()

        try{
          const colDefs = ref.current?.api.getColumnDefs() || [];
          const checkboxExists = colDefs.some((col: any) => col.field === "checkbox");
          if (checkboxExists) {
            dispatch(REMOVE_COLDEFS(["checkbox"]));
          }
          dispatch(UPDATE_IS_SAVING_DRAFT(true))
          let newData:any = []
          const errorOrWarning = activeMaster.rowData.find((row:any)=>(Object.keys(row).includes('error'))||(Object.keys(row).includes('warning')));
          if(errorOrWarning){
            newData = activeMaster.rowData.map((row:any)=>{
              const temp = {...row};
              if(!temp['error']){
                temp['error'] = '';
              }
              if(!temp['warning']){
                temp['warning'] = '';
              }
              return temp;
            });
          }
          else{
            newData = activeMaster.rowData;
          }
       
          const selectedData = ref.current?.api.getSelectedRows();

          if(activeMaster.id==10 || activeMaster.id==6){
            newData = newData.map((row:any)=>{
              const tempRow = {...row}
              if(selectedData?.find((selectedRow:any)=>JSON.stringify(selectedRow)===JSON.stringify(row))){
                tempRow.IsSelected = true
                return tempRow
              }
              tempRow.IsSelected = false
                return tempRow
            })
          }
          console.log(newData)
          const res = await postDraftChunks(newData)
          if(checkboxExists){
            addCheckBoxColDefs()
          }
          if(res){
            //dispatch(UPDATE_PROGRESS_STATE("savedToDraft"))
            if(draftID.length > 0){
              return notifySuccess("Draft Updated Successfully")
            }
            else{
              return notifySuccess("Draft Created Successfully")
            }
          }
          notifyError("Something Went Wrong")
          // if(activeMaster.progress==='uploaded'){
          //   addCheckBoxColDefs()
          // }
          return false
        }catch(err){
          notifyError("Something Went Wrong")
          // if(activeMaster.progress==='uploaded'){
          //   addCheckBoxColDefs()
          // }
          return false
        }finally{
          //dispatch(SET_DRAFT_ID(''));
          dispatch(UPDATE_IS_SAVING_DRAFT(false))
        }
    }

     
      const onReset = () => {
        const currentMasterData = masters.find((master:MDMMasterState)=>master.id === activeMaster.id)
        console.log("CURRENTMATTER",currentMasterData?.rowData)
        if(currentMasterData) dispatch(UPDATE_ROW_DATA(currentMasterData.rowData))
          const errorExist = currentMasterData?.rowData?.some((row: any) => row?.error !== undefined) || false;
          const warningExist = currentMasterData?.rowData?.some((row: any) => row?.warning !== undefined) || false;
        
          if(!errorExist){
            dispatch(REMOVE_COLDEFS(['error']));
          }
          if(!warningExist){
            dispatch(REMOVE_COLDEFS(['warning']));
          }
        //dispatch(REMOVE_COLDEFS(['error','warning']));
        dispatch(UPDATE_PROGRESS_STATE('editOnline'));
        setEnableEditOnlineReset(false)
        toggleEditOnline(false)
      }

      // const     validateEditOnlineData = (data:any[]) => {
      //   //Cleanup errors if any and provide clean copy to check again.
      //   //PS - Worked in tight deadline plz optimize whenever possible.
      //   dispatch(REMOVE_COLDEFS(['error','warning']));

      //   const rowData = data.map((row:any)=>{
      //     if(row.error || row.warning){
      //       return _.omit(row,'error','warning');
      //     }
      //     return row;
      //   })
      
      //   const newData = rowData.map((row:any)=>{
      //     const rowClone = {...row};
      //     const {error,warning} = checkError(rowClone,activeMaster,pageType);
          
      //     if(error){
      //       rowClone.error = error
      //     }
      //     else{
      //       rowClone.error = '';
      //     }
      //     if(warning){
      //       rowClone.warning = warning;
      //     }
      //     else{
      //       rowClone.warning = '';
      //     }
      //     return rowClone;
      //   });
        
      //   const isErrorPresent = newData.find((row:any)=>row.error);
      //   const isWarningPresent = newData.find((row:any)=>row.warning);
      
      //   if(isErrorPresent){
      //     addInvalidDataColDefs('error');
      //   }
        
      //   if(isWarningPresent){
      //     addInvalidDataColDefs('warning');
          
      //   }
      //   dispatch(UPDATE_ROW_DATA(newData));
      //   // if(isErrorPresent || isWarningPresent){
      //   //   return notifyError("Invalid Data Found. Please Clear all the errors and warnings before proceeding");
      //   // } 
      //   return newData;
      // }

      const onEditOnlineSave = async()=>{
        await onSaveToDraft();
      //  if(isSuccess){
      //   const result = validateEditOnlineData(activeMaster.rowData);
        
      //   const isErrorPresent = result.find((row:any)=>row.error.length > 0);
      //   const isWarningPresent = result.find((row:any)=>row.warning.length > 0);
      
      //   if(isErrorPresent || isWarningPresent){
      //     return notifyError("Please Clear All Errors before submit")
      //   }
      //   // dispatch(UPDATE_PROGRESS_STATE('editOnlineSaved'))
      //  }

      }

      const toggleUploadModal = (value:boolean)=>{
        dispatch(TOGGLE_UPLOAD_MODAL(value))
      }
       const onShowChart = async (rowData:any) => {
        try {
          const toastId = notifyLoader('Fetching Chart Details');
          const {data:{data}} = await getSeasonalityDetails(rowData);
          const seasonalityData = data[0];
          setSeasonalityRowData(rowData);
          setNormChangeData(seasonalityData.norm);
          const chartData = generateSesonalityChartData(rowData,seasonalityData);
          setChartData(chartData);
          toggleSeasonalityChartModal(true);
          toast.dismiss(toastId);
          notifySuccess("Chart Details Fetched Successfully");
          
        } catch (error) {
          toast.dismiss();
          toast.error("Something Went Wrong");

        }
        
      }

    
      const onSeasonalityQuickFilter = (statusId:number[])=>{
        const doesMasterExist = masters.find((master:MDMMasterState)=>master.id===activeMaster.id)
        let updatedSeasonalityActiveQuickFilter= [...seasonalityActiveQuickFilter];

        if(doesMasterExist){
          if(seasonalityActiveQuickFilter.find((s)=>JSON.stringify(s)===JSON.stringify(statusId))){
            updatedSeasonalityActiveQuickFilter = seasonalityActiveQuickFilter.filter((s)=>{
              return JSON.stringify(s)!==JSON.stringify(statusId)
            })
            setSeasonalityActiveQuickFilter(updatedSeasonalityActiveQuickFilter)
          }
          else{
            updatedSeasonalityActiveQuickFilter = [...updatedSeasonalityActiveQuickFilter,statusId]
            setSeasonalityActiveQuickFilter(updatedSeasonalityActiveQuickFilter)
          }
          let updatedRowData = []
          

          const flatState = _.flatMap(updatedSeasonalityActiveQuickFilter)
          if(flatState.length==0){
            updatedRowData=doesMasterExist.rowData;
          }
          else{
            updatedRowData = doesMasterExist.rowData.filter((row:any)=>{     
              return flatState.includes(row.sts)
            })
          }
          
          dispatch(UPDATE_ROW_DATA(updatedRowData))
          dispatch(SET_RECORD_COUNT(updatedRowData.length))
        
        }
        else{
          return 
        }
      }

    //   const onDeleteOnlineSave = ()=>{
    //     const selectedRows = ref.current?.api.getSelectedRows()
    //     if(!selectedRows || selectedRows.length<1)return notifyError('Please select rows to submit')
    //     dispatch(REMOVE_COLDEFS(['checkbox']))
    //     dispatch(UPDATE_ROW_DATA(selectedRows))
    //     dispatch(UPDATE_PROGRESS_STATE('deleteOnlineSaved'))
    // }
    const onReviewConflicts = ()=>{
      console.log("ACTIVEMASTER",activeMaster.colDefs)
      const newColDefs:ColDef[] = activeMaster.colDefs.map((colDef:ColDef)=>{
        return {
          ...colDef,
          // cellRenderer:'conflictErrorCellRenderer',
          // tooltipField:colDef.field,
          cellRenderer:'conflictErrorCellRenderer',
          ccellStyle: (params:any) => {
            const baseStyle = { ...params.colDef.cellStyle };
            if (params.colDef.colId !== 'checkbox') {
              baseStyle.padding = 0;
            }
            return baseStyle;
          }
          // onCellClicked:(params:any)=>console.log(params)
          // tooltipField:colDef.field

        }
      })

     if(newColDefs) dispatch(UPDATE_COLDEFS(newColDefs))
      const exists = activeMaster.colDefs.some(obj => obj.colId === "checkbox");
       if(!exists){
        addCheckBoxColDefs()
      }
      dispatch(UPDATE_ROW_DATA(conflictData))
      setIsConflictModalOpen(false)
      dispatch(SET_RECORD_COUNT(conflictData.length))
    }

    const onIgnoreSubmitErrors = ()=>{
      const errorRowData = createErrorRowData(errorData,activeMaster.id)
      if(errorRowData.length>0){
        addInvalidDataColDefs('error')
        dispatch(UPDATE_ROW_DATA(errorRowData))
        dispatch(SET_RECORD_COUNT(errorRowData.length))
      }
      if(activeMaster.progress==='editOnlineConflicts')dispatch(UPDATE_PROGRESS_STATE('editOnlineSubmitted'));
      else dispatch(UPDATE_PROGRESS_STATE('submitted'));
      dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
      
      setIsConflictModalOpen(false)
    }


    return {
        colDefs,
        isSelectMasterOpen,
        isSavingToDraft,
        options,
        selectedOptions,
        activeMaster,
        filterButtonStatus,
        setFilterButtonStatus,
        getSelectedMasters,
        handleSelectMasterSubmit,
        handleTabChange,
        handleTabClose,
        addNewMaster,  
        handleOnAddFilter,
        handleOnDeleteFilter,
        allMastersState,
        handleApplyFilter,
        isLoading,
        isWarningModalOpen,
        toggleWarningModal,
        onWarningModalClose,
        onWarningModalSuccess,
        isUploadModalOpen,
        toggleUploadModal,
        recordCount,
        downloadFileName,
        setDownloadFileName,
        onUploadMaster,
        isOverlayVisible,
        file,
        setFile,
        isTableDataLoading,
        exportToExcel,
        onColumnChange,
        onBackButton,
        onBackButton1,
        onClearExportError,
        agGridProps,
        ref,
        tempRef,
        tempGridData,
        tempAgGridProps,
        deleteSelected,
        onSubmit,
        onSaveToDraft,
        isUploadButtonDisabled,
        editOnline,
        onEditOnline,
        rowsPerPage,
        selectedRowsCount,
        currentPage,
        seasonalityActiveQuickFilter,
        // onSaveToDraft,
        onSeasonalityQuickFilter,
        handleChangePage,
        onReset,
        onEditOnlineSave,
        chartData,
        defaultToolPanel,
        isSeasonalityChartModalOpen,
        normChangeData,
        toggleSeasonalityChartModal,
        seasonalityRowData,
        isShowAll,
        conflictCount,
        errorCount,
        submittedDataCount,
        conflictData,
        errorData,
        isConflictModalOpen,
        setIsConflictModalOpen,
        onReviewConflicts,
        onIgnoreSubmitErrors,
        isDataAvailableLocally,
        onSeasonalityStatusUpdate,
        validResumeStatuses,
        validStopStatuses,
        onPIPOStatusUpdate,
        enableEditOnlineReset,
        uploadProgress,
        totalProgress,
        tempRecordCount,
        isSubmitDisabled,
        onDiscardDraftCallback,
        canToggleMaster,
        setCanToggleMaster,
        getAllVisibleColums,
    }
}

export default useViewModify;