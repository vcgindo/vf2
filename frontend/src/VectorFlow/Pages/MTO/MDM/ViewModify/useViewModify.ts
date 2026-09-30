import { ColDef, SideBarDef } from "ag-grid-enterprise";
import { AgGridReactProps } from "ag-grid-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import ErrorCell from "../../../../../components/VectorFLOW/commons/ErrorCell";
import {
  notifyError,
  notifyLoader,
  notifyPromise,
  notifySuccess,
} from "../../../../../helpers/notify";
import {
  areMasterFiltersValid,
  createConflictRowData,
  createErrorRowData,
  generateOptions,
  generateSesonalityChartData,
  getActionId,
  getCCRNamesFromId,
  mapMasterToMasterState,
  mapStateFiltersToPayload,
  parseMTOExcelData,
} from "../../../../../helpers/utils";
import {
  ADD_COLDEFS,
  ADD_FILTER,
  FILL_MASTERS,
  FILL_OPTIONS,
  REMOVE_ALL_FILTERS,
  REMOVE_COLDEFS,
  REMOVE_FILTER,
  REMOVE_MASTER,
  REMOVE_ROW_DATA,
  RESET_FILTERS,
  RESET_STATE,
  SET_DRAFT_ID,
  SET_RECORD_COUNT,
  STORE_ALL_MASTERS,
  SYNC_ACTIVE_MASTER_TO_MASTER,
  TOGGLE_SELECT_MASTER_SCREEN,
  TOGGLE_UPLOAD_MODAL,
  UPDATE_ACTIVE_MASTER,
  UPDATE_COLDEFS,
  UPDATE_DATA_AVAILABILITY_STATUS,
  UPDATE_PROGRESS_STATE,
  UPDATE_ROW_DATA,
} from "../../../../../redux/actions/MDM";
import { type RootState } from "../../../../../redux/store/store";
import {
  useCreateDraft,
  useDeleteMTODraft,
  useDeleteTask,
  useGetBufferMasterData,
  useGetBufferTypeMaster,
  useGetCalendarMasterData,
  useGetCCRMasterData,
  useGetMTOMasterUIConfiguration,
  useGetPOOGIMasterData,
  useGetSeasonalityDetails,
  useModifyDraft,
  useModifyMasterData,
  useModifyMasterDataRetail,
  useSaveBufferMasterDraft,
  useSaveBufferMasterTask,
  useSaveCalendarMasterDraft,
  useSaveCalendarMasterTask,
  useSaveCCRMasterDraft,
  useSaveCCRMasterTask,
  useSavePOOGIMasterDraft,
  useSavePOOGIMasterTask,
} from "../../../../Services/MTA/MDM";
import {
  type Field,
  type GetMasterDataPayload,
  type GridRef,
  type MDMMasterState,
  type Option,
  type QueryFilteredDataConfigs,
} from "../../../../types/MDM";

import _ from "lodash";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { v4 as uuidv4 } from "uuid";
import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader";
import WarningCell from "../../../../../components/VectorFLOW/commons/WarningCell";
import { useUserData } from "../../../../../context";
import {
  RESET_MTO_STATE,
  SET_BUFFER_INITIAL_DATA,
  SET_BUFFER_MODIFY_DATA,
  SET_CALENDAR_INITIAL_DATA,
  SET_CCR_INITIAL_DATA,
  SET_CCR_MODIFY_DATA,
  SET_POOGI_INITIAL_DATA,
  SET_POOGI_MODIFY_DATA
} from "../../../../../redux/actions/MTO";
import {
  useGetCCRMasterData as useGetCCRMasterDataForCalender,
  useGetDeptMasterData,
  useGetPlantMasterData
} from "../../../../../VectorFlow/Services/MTO/Common/Masters";
import { useGetCCRGroupMaster } from "../../../../../VectorFlow/Services/MTO/Production/DueDateQuotation";
import AddRemoveCellRenderer from "./AddRemoveCellRenderer";
import ConflictErrorCellRenderer from "./ConflictErrorCellRenderer";
import DaysOfWeekRenderer from "./DaysOfWeekRenderer";
import MajReasonDescCell from "./MajReasonDescCell";
import { CALENDAR_Add_VALIDATION_SCHEMA, CALENDAR_VALIDATION_SCHEMA } from "./MDMJoiValidations";
import MinReasonDescCell from "./MinReasonDescCell";
import MTOCalendarEditCellRenderer from "./MTOCalendarEditCellRenderer";
import MTOErrorWarningCell from "./MTOErrorWarningCell";
import PoogiEditDeleteCell from "./PoogiEditDeleteCell";
import ToggleButton from "./ToggleButton";
import moment from "moment";
import {CustomStatusPanel } from "../CustomStatusPannel";
import { validateBuffer, validateCCR } from "./CommonUtils";

const useViewModify = (pageType: string) => {
  const dispatch = useDispatch();
  const user = useUserData();
  const themeUi = user.user.theme_ui
  const options = useSelector((state: RootState) => state.mdm.options);
  const selectedOptions = useSelector(
    (state: RootState) => state.mdm.selectedOptions
  );
  const activeMaster = useSelector(
    (state: RootState) => state.mdm.activeMaster
  );
  const masters = useSelector((state: RootState) => state.mdm.masters);
  const isSelectMasterOpen = useSelector(
    (state: RootState) => state.mdm.isSelectMasterOpen
  );
  const isUploadModalOpen = useSelector(
    (state: RootState) => state.mdm.isUploadModalOpen
  );
  const draftID = useSelector((state: RootState) => state.mdm.draftId);
  const chunkSize = useSelector((state: RootState) => state.mdm.chunkSize);
  const recordCount = useSelector((state: RootState) => state.mdm.recordCount);
  const isDataAvailableLocally = useSelector(
    (state: RootState) => state.mdm.isDataAvailableLocally
  );

  const [tempRecordCount, setTempRecordCount] = useState<number>(0);

  const [allMastersState, setAllMasterState] = useState<MDMMasterState[]>([]);
  const [isWarningModalOpen, toggleWarningModal] = useState<boolean>(false);
  const [isShowAll, setIsShowAll] = useState<boolean>(true);
  const [isOverlayVisible, setIsOverlayVisible] = useState<boolean>(false);
  // const [isUploadModalOpen,toggleUploadModal] = useState<boolean>(false)
  // const [recordCount,setRecordCount] = useState<number>(0)
  const [downloadFileName, setDownloadFileName] = useState("");
  const [file, setFile] = useState<File>();
  const [isTableDataLoading, setIsTableDataLoading] = useState<boolean>(false);
  const [defaultToolPanel, setDefaultToolPanel] = useState<string>("");
  const [downloadData, setDownloadData] = useState<boolean>(false);
  const [tempDownloadData, setTempDownloadData] = useState<boolean>(false);
  const [colDefs, setColDefs] = useState<ColDef[]>([]);
  const [isUploadButtonDisabled, setIsUploadButtonDisabled] =
    useState<boolean>(true);
  const [chartData, setChartData] = useState<object>();
  const [isSeasonalityChartModalOpen, toggleSeasonalityChartModal] =
    useState<boolean>(false);
  const [normChangeData, setNormChangeData] = useState<any>([]);
  const [enableEditOnlineReset, setEnableEditOnlineReset] =
    useState<boolean>(false);

  const [conflictCount, setConflictCount] = useState<number>(0);
  const [errorCount, setErrorCount] = useState<number>(0);
  const [conflictData, setConflictData] = useState<Array<any>>([]);
  const [errorData, setErrorData] = useState<Array<any>>([]);
  const [submittedDataCount, setSubmittedDataCount] = useState<number>(0);
  const [isConflictModalOpen, setIsConflictModalOpen] =
    useState<boolean>(false);

  const [editOnline, toggleEditOnline] = useState(false);
  const [selectedRowsCount, setSelectedRowsCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = useMemo(() => {
    if (pageType === "add")
      return parseInt(process.env.REACT_APP_ADDRECORD_PAGE || "50");
    else if (pageType === "remove")
      return parseInt(process.env.REACT_APP_DELETERECORD_PAGE || "50");
    else return parseInt(process.env.REACT_APP_VIEWRECORD_PAGE || "50");
  }, []);
  const [isSubmitDisabled, setIsSubmitDisabled] = useState(false);

  const [seasonalityActiveQuickFilter, setSeasonalityActiveQuickFilter] =
    useState<Array<Array<number>>>([]);
  const ref = useRef<GridRef>();
  const tempRef = useRef<GridRef>(); //used for second ag grid instance which is hidden.
  const [tempGridData, setTempGridData] = useState<object[]>([]);

  const [filterButtonStatus, setFilterButtonStatus] = useState<Array<number>>(
    []
  );
  const [seasonalityRowData, setSeasonalityRowData] = useState<any>([]);


  const {
    mutateAsync: MTOMasterUIConfiguration, isLoading /*isLoading: MTOBufferLoading*/,
  } = useGetMTOMasterUIConfiguration();
  // collect all hook;
  const { mutateAsync: saveBufferMasterTask, isLoading: isSaveBufferMasterTask } = useSaveBufferMasterTask();
  const { mutateAsync: saveCCRMasterTask, isLoading: isSaveCCRMasterTask } = useSaveCCRMasterTask();
  const { mutateAsync: saveBufferMasterDraft, isLoading: isSaveBufferMasterDraft } = useSaveBufferMasterDraft();
  const { mutateAsync: savePOOGIMasterTask, isLoading: isSavePOOGIMasterTask } = useSavePOOGIMasterTask();
  const { mutateAsync: savePOOGIMasterDraft, isLoading: isSavePOOGIMasterDraft } = useSavePOOGIMasterDraft();
  const { mutateAsync: saveCalendarMasterTask, isLoading: isSaveCalendarMasterTask } = useSaveCalendarMasterTask();
  const { mutateAsync: saveCalendarMasterDraft, isLoading: isSaveCalendarMasterDraft } = useSaveCalendarMasterDraft();
  const { mutateAsync: saveCCRMasterDraft, isLoading: isSaveCCRMasterDraft } = useSaveCCRMasterDraft();
  const { mutateAsync: GetBufferTypeMaster, isLoading: isGetBufferTypeMaster } = useGetBufferTypeMaster();
  const { mutateAsync: getBufferMasterData, isLoading: isGetBufferMasterData } = useGetBufferMasterData();
  const { mutateAsync: createDraft, isLoading: isCreateDraft } = useCreateDraft();
  const { mutateAsync: getPOOGIMasterData, isLoading: isGetPOOGIMasterData } = useGetPOOGIMasterData();
  const { mutateAsync: getCalendarMasterData, isLoading: isGetCalendarMasterData } = useGetCalendarMasterData();
  const { mutateAsync: modifyDraft, isLoading: isModifyDraft } = useModifyDraft();
  const { mutateAsync: deleteDraft, isLoading: isDeleteDraft } = useDeleteMTODraft();
  const { mutateAsync: modifyMaster, isLoading: isModifyMaster } = useModifyMasterData();
  const { mutateAsync: modifyMasterRetail, isLoading: isModifyMasterRetail } = useModifyMasterDataRetail();
  const { mutateAsync: deleteTask, isLoading: isDeleteTask } = useDeleteTask();
  const { mutateAsync: getCCRMasterData, isLoading: isGetCCRMasterData } = useGetCCRMasterData();
  const { mutateAsync: getCCRMasterDataForCalender, isLoading: isGetCCRMasterDataForCalender } = useGetCCRMasterDataForCalender();
  const { mutateAsync: getPlantMaster, isLoading: isGetPlantMaster } = useGetPlantMasterData();
  const { mutateAsync: getDeptMaster, isLoading: isGetDeptMaster } = useGetDeptMasterData();
  const { mutateAsync: getCCRGroupMaster, isLoading: isGetCCRGroupMaster } = useGetCCRGroupMaster();
  
  const loadingStates = [
    isSaveBufferMasterTask,
    isSaveCCRMasterTask,
    isSaveBufferMasterDraft,
    isSavePOOGIMasterTask,
    isSavePOOGIMasterDraft,
    isSaveCalendarMasterTask,
    isSaveCalendarMasterDraft,
    isSaveCCRMasterDraft,
    isGetBufferTypeMaster,
    isGetBufferMasterData,
    isCreateDraft,
    isGetPOOGIMasterData,
    isGetCalendarMasterData,
    isModifyDraft,
    isDeleteDraft,
    isModifyMaster,
    isModifyMasterRetail,
    isDeleteTask,
    isGetCCRMasterData,
    isGetCCRMasterDataForCalender,
    isGetPlantMaster,
    isGetDeptMaster,
    isGetCCRGroupMaster,
    // add more as needed
  ];
  
  const isAPILoading = useMemo(() => loadingStates.some(Boolean), [loadingStates]);  

  const [bufferTypeData, setBufferTypeData] = useState<any>(undefined);

  const [TASK_ID, setTaskId] = useState<string>("");

  const [uploadProgress] = useState("");

  /***Add the below line to fetch MTO Buffer */
  const [totalProgress] = useState("");

  // const [isDataAvailableLocally,setIsDataAvailableLocally] = useState(false);

  // const allMasters:Master[] = masterUIConfiguration?.data.data || [];

  // const allMastersState:MDMMasterState[] = mapMasterToMasterState(allMasters);

  const validStopStatuses = [1, 2, 3, 4, 5, 6, 21];

  const validResumeStatuses = [23];

  const {bufferInitialData,ccrInitialData,bufferModifyData,ccrModifyData, calendarInitialData} = useSelector(
    (state: any) => state.mto
  );
  
  const [mtoProgress, setMTOProgress] = useState("initial");

  const poogiModifyData = useSelector(
    (state: any) => state.mto.poogiModifyData
  );
  const poogiInitialData = useSelector(
    (state: any) => state.mto.poogiIntialData
  );

  const [selectedMajReason, setSelectedMajReason] = useState<any>("");
  const [showModal, setShowModal] = useState(false);
  
  const invalidDataColdefs: ColDef[] = [
    {
      field: "warning",
      colId: "warning",
      headerName: "Warning",
      floatingFilter: false,
      cellRenderer: "warningCell",
      minWidth: 200,
      suppressColumnsToolPanel: true,
      wrapText: true,
      autoHeight: true,
    },
    {
      field: "error",
      colId: "error",
      headerName: "Error",
      floatingFilter: false,
      cellRenderer: "errorCell",
      suppressColumnsToolPanel: true,
      wrapText: true,
      autoHeight: true,
      minWidth: 300
    },
  ];

  const onColumnChange = () => {
    const localColDefs = ref.current?.api.getColumnDefs();
    if (ref.current && localColDefs) {
      dispatch(UPDATE_COLDEFS(localColDefs));
      dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
      setDefaultToolPanel("columns");
    }
  };

  const customCellRenderers = useMemo(
    () => ({
      loadingOverlay: VFLoader,
      errorCell: ErrorCell,
      warningCell: WarningCell,
      conflictErrorCellRenderer: ConflictErrorCellRenderer,
      poogiEditDeleteCellRenderer: PoogiEditDeleteCell,
      DaysOfWeekRenderer: DaysOfWeekRenderer,
    }),
    []
  );

  const [ccrsData, setCcrsData] = useState<any>([]);
  const [plantMaster, setPlantMaster] = useState<any>([]);
  const [deptMaster, setDeptMaster] = useState<any>([]);
  const [ccrGroupMaster, setCCRGroupMaster] = useState<any>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [plantNames, setPlantNames] =  useState<any>([]);
  const [ccrNames, setCCRNames]= useState([]);
  const [selectedData, setSelectedData] = useState<any>({});
  const location = useLocation();
  const prevPath: string | undefined  = location?.state?.backUrl.split('/').pop();
  const backUrl = location?.state?.backUrl || "";
  const navigate = useNavigate()
  const saveDraft = "saved-drafts"
  // adding all ccrName in ccr_names array
  const ccr_names :string[] = []
  for(const ccr of ccrsData){
    ccr_names.push(ccr.cnm)
  }
  const [calendarFormData, setCalendarFormData] = useState({});
  const CCRGroupMaterSetRef = useRef<Set<string>>(new Set());
  const [isDisabled, setIsDisabled] = useState(true);
  const clearGridFilter = () =>{
    ref?.current?.api.setFilterModel(null);
      setIsDisabled(true);
  }

  useEffect(() => {
    setColDefs(activeMaster.colDefs);

    if (filterButtonStatus.length !== 0) return;
    
    const allOptions: Option[] = generateOptions(allMastersState);
    dispatch(STORE_ALL_MASTERS(allMastersState));
    dispatch(FILL_OPTIONS(allOptions));
   
    // if(isToolPanelOpen) ref.current?.api.openToolPanel('columns');
  }, [selectedOptions, activeMaster, allMastersState]);

  const getInitialData = async () => {
    if (activeMaster.id === 501) {
      const result = await getBufferMasterData({});
      dispatch(SET_BUFFER_INITIAL_DATA(result.data.data));
      setRowDataInitial(result);
    }
    if (activeMaster.id === 502) {
      const result = await getCCRMasterData({});
      dispatch(SET_CCR_INITIAL_DATA(result.data.data));
      setRowDataInitial(result);
    }
    if (activeMaster.id === 503) {
      const result = await getPOOGIMasterData({});
      dispatch(SET_POOGI_INITIAL_DATA(result.data.data));
      setRowDataInitial(result);
    }
    if (activeMaster.id === 504) {
      const result = await getCalendarMasterData();
      const ccrs = await getCCRMasterData({});
      setCcrsData(ccrs.data.data || []);
      if(result && result.data){

      dispatch(SET_CALENDAR_INITIAL_DATA(result.data.data));
      setRowDataInitial(result);
      }
    }
  };

  const setRowDataInitial = (result: any) => {

    if (pageType === "add") return;

    const rawData = result?.data?.data ?? [];
    const tempRowData = rawData.map((row: any) => {
      const newRow = { ...row };
      Object.entries(newRow).forEach(([key, value]: any) => {
        const colDef = colDefs.find((c) => c.colId === key);
        if (colDef?.cellDataType === "number" && value !== null) {
          newRow[key] = parseFloat(value);
        }
      });
      return newRow;
    });
    dispatch(UPDATE_ROW_DATA(tempRowData));
    dispatch(SET_RECORD_COUNT(tempRecordCount));
    dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
    
  };
  
  const getPlantMasterData = async () => {
    const response = await getPlantMaster();
    setPlantMaster(response.data.data);
    setPlantNames(response.data.data || [])
  };

  const getCCRMasterDataCalender  = async () =>{
    const response = await getCCRMasterDataForCalender();
    setCCRNames(response.data.data|| [])
  }
  
  const getDeptMasterData = async () => {
    const response = await getDeptMaster();
    setDeptMaster(response.data.data);
  };
  const getCCRGroupMasterData = async () => {
    const response = await getCCRGroupMaster();
    setCCRGroupMaster(response.data.data);
  };


  useEffect(() => {
    if (activeMaster.id === 501 && !bufferTypeData) {
      getBufferMasterDataType();
    }
    if (
      activeMaster.id === 503 ||
      activeMaster.id === 502 ||
      activeMaster.id === 504
    ) {
      getPlantMasterData();
      getCCRMasterDataCalender();
    }
    if (activeMaster.id === 502) {
      getDeptMasterData();
      getCCRGroupMasterData();
    }
    else if(activeMaster.id===504){
      getCCRGroupMasterData();

    }
    getInitialData();
  }, [activeMaster.id]);

  const getUpdatedColDefs = ({
    colDefs,
    activeMaster,
    bufferTypeData,
    plantMaster,
    deptMaster,
    ccrGroupMaster,
    ccr_names,
  }: any) => {
    if (!colDefs || !Array.isArray(colDefs)) return [];

    const clonedColDef = _.cloneDeep(activeMaster.colDefs);
  
    const commonStyle = (params: any) => {
      const { data } = params;
      if (params?.colDef?.colId !== "actions" && data?.isdel) { 
        return {
          filter: "blur(1px)",
          opacity: 0.6,
          transition: "all 0.3s ease-in-out",
          backgroundColor: "#f0f0f0",
        }
      } else if (data.ia || data.iu) {
        return { color: "rgb(128, 0, 64)" };
      }
      return {};
    };
  
    const newColDef =  clonedColDef.map((col: any) => {
      const baseCol = { ...col };
  
      // 🔹 Common: Disable editing on 'actions' and 'iv'
      if (["iv"].includes(col.field)) {
        return {
          ...baseCol,
          filter: false,
          floatingFilter: false,
          cellRenderer: ToggleButton,
          pinned: "right",
        };
      }
  
      // 🔹 Common rule for editable fields
      const editable = (params: any) => {
        if (["iv", "actions", "pactions","err"].includes(col.field)) {
          return false;
        } else if (pageType === "add") {
          return true;
        } else {
          if (activeMaster.id === 503) {
            return params.data.ia === true
          } else {
            return params.data.editable === true
          }
        }
      };

      // 🔹 Common dropdowns
      const dropdowns: any = {
        bt: bufferTypeData?.map((i: any) => i.id),
        pl: plantMaster?.map((i: any) => i.plant_id),
        plnm: plantMaster?.map((i: any) => i.plant_name),
        pid: plantMaster?.map((i: any) => i.plant_id),
        dp: deptMaster?.map((i: any) => i.dept_id),
        cgid: Object.keys(ccrGroupMaster || {}),
        ccrId: ccr_names,
        ib: [true, false]
      };
  
      // 🔹 Handle field-specific editors
      if (col.field === "bt") {
        return {
          ...baseCol,
          editable,
          cellEditor: "agRichSelectCellEditor",
          cellEditorParams: {
            values: dropdowns.bt,
            formatValue: (id: any) => getCategoryName(id),
          },
          valueGetter: (params: any) => getCategoryName(params?.data?.bt),
          filter: "agMultiColumnFilter",
          cellStyle: commonStyle,
        };
      }
  
      if (["pl", "plnm", "pid", "dp", "cgid", "ccrId"].includes(col.field)) {
        return {
          ...baseCol,
          editable,
          cellEditor: "agRichSelectCellEditor",
          cellEditorParams: {
            values: dropdowns[col.field],
            formatValue: (id: any) => myCCRFormatter(id, col.field, true),
          },
          valueGetter: myCCRFormatter,
          cellStyle: commonStyle,
        };
      }
  
      if (["slt", "mlt", "bsz", "rb", "cpd", "whpd", "sh", "fh", "cwl"].includes(col.field)) {
        return {
          ...baseCol,
          editable,
          cellEditor: "agNumberCellEditor",
          cellEditorParams: { min: 0, max: 1000000 },
          cellStyle: commonStyle,
        };
      }
  
      if (["bcd", "bd"].includes(col.field)) {
        return { ...baseCol, editable, cellStyle: commonStyle };
      }
  
      if (col.field === "ib") {
        return {
          ...baseCol,
          editable,
          cellEditor: "agRichSelectCellEditor",
          cellEditorParams: {
            values: dropdowns[col.field],
          },
          valueFormatter: (params: any) => {
            if (params.value === null || params.value === undefined ) return "";
            const value = params.value;
            return value === true || value === "true" ? "True" : "False";
          },
          cellStyle: commonStyle
        };
      }
  
      if (["sd", "ed"].includes(col.field)) {
        return {
          ...baseCol,
          editable,
          cellDataType: "date",
          cellEditor: "agDateCellEditor",
          valueFormatter: (params: any) => {
            if (!params.value) return "";
            const date = new Date(params.value);
            return date.toLocaleDateString("en-CA");
          },
        };
      }
  
      if (activeMaster.id === 503) {
        return {
          ...baseCol,
          editable,
          valueFormatter: myCCRFormatter,
          cellStyle: (params: any) => {
            const d = params.data;
            if (
              d?.majId?.toString().startsWith("m") ||
              d?.minId?.toString().startsWith("m") ||
              d?.iu === true ||
              d?.id === true ||
              d?.ie === false
            ) {
              return { color: "rgb(128, 0, 64)" };
            }
            return {};
          },
        };
      }
  
      if (activeMaster.id === 504) {
        return {
          ...baseCol,
          editable,
          cellStyle: (params: any) => {
            const d = params.data;
            if (d?.id)
              return {
                filter: "blur(1px)",
                opacity: 0.4,
                transition: "all 0.3s ease-in-out",
                backgroundColor: "#f0f0f0",
              };
            if (d?.iu || d?.ia) return { color: "rgb(173, 5, 89)" };
            return {};
          },
        };
      }
  
      // 🔹 Default case
      return {
        ...baseCol,
        editable,
        cellStyle: commonStyle,
      };
    });

    return newColDef;
  };

  useEffect(() => {
    if (!activeMaster.colDefs?.length) return;
  
    if (
      (activeMaster.id === 501 && bufferTypeData) ||
      (activeMaster.id === 502 && ccrGroupMaster && plantMaster && deptMaster)
    ) {
      const newColDef = getUpdatedColDefs({
        colDefs: activeMaster.colDefs,
        activeMaster,
        bufferTypeData,
        ToggleButton,
        plantMaster,
        deptMaster,
        ccrGroupMaster,
        ccr_names,
        prevPath,
        saveDraft,
      });
  
      if (!newColDef.find((col: any) => col.colId === "actions") && prevPath === saveDraft && pageType === "modify") {
        
        dispatch(UPDATE_COLDEFS([actionsCol(false), ...newColDef]));

      } else {

        dispatch(UPDATE_COLDEFS([...newColDef]));
      }
    }
  }, [activeMaster.id, activeMaster.rowData, bufferTypeData, plantMaster, deptMaster, ccrGroupMaster]);
  
  
  // useEffect(() => {
  //   if (activeMaster.id === 501) {
  //     if (bufferTypeData) {
  //       const newColDef = _.cloneDeep(activeMaster.colDefs);
  //       // Iterate over the column definitions and update based on colId
  //       newColDef.forEach((col: any) => {
  //         if (col.colId === "bt") {
  //           col.cellEditorParams = {
  //             values: bufferTypeData?.map((item: any) => item.id),
  //             formatValue: (id: any) => getCategoryName(id)
  //           };
  //           col.valueGetter = (params: any) => {
  //             return getCategoryName(params?.data?.bt)
  //           }
  //           col.filter = 'agTextColumnFilter';
  //         }
  //         if (col.colId === "iv") {
  //           col.cellRenderer = ToggleButton;
  //           col.pinned = 'right';
  //           col.filter = false;
  //         }
  //       });
  //       newColDef.forEach((ele: any) => {
  //         ele.cellStyle = (params: any) => {
  //           if (
  //             params.data.bid === null ||
  //             params.data.bid === undefined ||
  //             params.data.iv === false
  //           ) {
  //             return { color: "rgb(128, 0, 64)" };
  //           }
  //         };
  //       });
        
  //       dispatch(UPDATE_COLDEFS([...newColDef]));
  //     }
  //   }
  // }, [bufferTypeData]);
  
  // useEffect(() => {
  //   if (
  //     (activeMaster.id===501 || activeMaster.id === 502 || activeMaster.id === 503 || activeMaster.id === 504) &&
  //     ccrGroupMaster &&
  //     plantMaster &&
  //     deptMaster &&
  //     activeMaster.colDefs.length > 0
  //   ) {
  //     const newColDef: any = _.cloneDeep(activeMaster.colDefs);

  //     // Iterate over the column definitions and update based on colId
  //     newColDef.forEach((col: any) => {
  //       if (col.colId === "iv") {
  //         col.cellRenderer = ToggleButton;
  //         col.pinned = 'right';
  //         col.filter = false;
  //         col.floatingFilter = false
  //       }
  //       if (col.colId === "bt") {
  //         col.cellEditorParams = {
  //           values: bufferTypeData?.map((item: any) => item.id),
  //           formatValue: (id: any) => getCategoryName(id)
  //         };
  //         col.valueGetter = (params: any) => {
  //           return getCategoryName(params?.data?.bt)
  //         }
  //         col.filter = 'agTextColumnFilter';
  //       }

  //       if(col.colId !== "actions" && col.colId !== "iv"){
  //         col.cellStyle = (params:any)=>{
  //           const { data } = params;
  
  //           if (data?.isdel ) {
  //             return { 
  //               filter: "blur(1px)",
  //               opacity: 0.6,
  //               transition: "all 0.3s ease-in-out",
  //               backgroundColor: "#f0f0f0", 
  //             }
  //           } else if(data?.ia){
  //             return { color: "rgb(173, 5, 89)" };
  //           }
  //           return {};
  //         }
  //       }
          
        
  //     });

  //     if (activeMaster.id === 502) {
  //       newColDef.forEach((ele: any) => {
  //         if(ele.colId !== "actions" && ele.colId !== "iv"){
  //           ele.cellStyle = (params:any)=>{
  //             const { data } = params;
    
  //             if (data?.isdel ) {
  //               return { 
  //                 filter: "blur(1px)",
  //                 opacity: 0.6,
  //                 transition: "all 0.3s ease-in-out",
  //                 backgroundColor: "#f0f0f0", 
  //               }
  //             } else if(data?.ia){
  //               return { color: "rgb(173, 5, 89)" };
  //             }
  //             return {};
  //           }
  //         }
  //         ele.valueFormatter = myCCRFormatter;
  //       });
  //     } else if (activeMaster.id === 503) {
  //       newColDef.forEach((ele: any) => {
  //         ele.cellStyle = (params: any) => {
  //           if (
  //             params.data.majId?.toString().startsWith("m") ||
  //             params.data.minId?.toString().startsWith("m") ||
  //             params.data.iu === true ||
  //             params.data.id === true ||
  //             params.data.ie === false
  //           ) {
  //             return { color: "rgb(128, 0, 64)" };
  //           }
  //         };
  //         ele.valueFormatter = myCCRFormatter;
  //       });
  //     } else if(activeMaster.id === 504){
  //       newColDef.forEach((ele:any)=>{
  //         if(ele.headerName !== "Action"){

  //           ele.cellStyle = (params: any) => {
  //             const { data } = params;
              
  //             if (data?.id ) {
  //               return { 
  //                 filter: "blur(1px)",
  //                 opacity: 0.4,
  //                 transition: "all 0.3s ease-in-out",
  //                 backgroundColor: "#f0f0f0", 
  //               }
  //             } else if (data?.iu) {
  //               return { color: "rgb(173, 5, 89)" };
  //             }else if(data?.ia){
  //               return { color: "rgb(173, 5, 89)" };
  //             }
  //             return {}; // ensure a default return to avoid undefined
  //           }
  //         }
  //       })
  //     }
  //     if(!newColDef.find((col:any)=> col.colId === "actions") && prevPath === saveDraft && activeMaster.id !== 503 && activeMaster.id !== 504 && pageType === "modify"){
        
  //       dispatch(UPDATE_COLDEFS([actionsCol(false),...newColDef]));

  //     }else{

  //       dispatch(UPDATE_COLDEFS([...newColDef]));
  //     }
  //   }
  // }, [ccrGroupMaster, plantMaster, deptMaster, activeMaster.id,activeMaster.rowData]);

  useEffect(() => {
    if (masters.length > 0 && filterButtonStatus.length !== 0) {
      setFilterButtonStatus(masters.map((master: MDMMasterState) => master.id));
    }
  }, [masters]);

  useEffect(() => {
    if (activeMaster.progress === "editOnline") {
      return onEditOnline("editOnline");
    }
    if (activeMaster.progress === "deleteOnline") {
      return onEditOnline("deleteOnline");
    }
  }, [activeMaster.progress]);

  useEffect(() => {
    const getMasterUIConfigurationData = async () => {
      try {
        const { data } = await MTOMasterUIConfiguration();
        if(pageType==='add'){
          setAllMasterState(mapMasterToMasterState(data.data).map((e: any) => {
            if (e.id === 501 || e.id === 502) {
              e.fields = e.fields.filter((field: any) => field.key !== "iv");
              e.colDefs = e.colDefs.filter((col: any) => col.colId !== "iv");
            }
            if (e.id === 504) {
              e.fields = e.fields.filter((field: any) => field.key !== "dow");
              e.colDefs = e.colDefs.filter((col: any) => col.colId !== "dow");
            }
            return e;
            }))
        }
        else{
          setAllMasterState(mapMasterToMasterState(data.data));

        }
      } catch (e) {
        console.error(e);
      }
    };
    getMasterUIConfigurationData();
  }, [pageType]);


  useEffect(() => {
    if (activeMaster.progress === "default" && pageType === "add") {
      dispatch(TOGGLE_UPLOAD_MODAL(true));
    }
  }, [activeMaster]);

  const ccrGroupValidationFn = useCallback(() => {
    try {
      if (CCRGroupMaterSetRef.current) {
        const tempSet = new Set<string>();

        Object.entries(ccrGroupMaster).forEach((entry: any) => {
          const [key, value] = entry
          if (value?.ccr_group_id != null) {
            tempSet.add(String(value.ccr_group_id));
          }
          tempSet.add(String(key));
        });

        CCRGroupMaterSetRef.current = tempSet;
      }
    } catch (e) {
      console.error(e);
    }

  }, [ccrGroupMaster]);
    
  useEffect(() => {
    ccrGroupValidationFn();
  }, [ccrGroupValidationFn]);


  // Validation in process....
  const validateMTOMaster = (masterId: number, newRowData: any) => {
    if (masterId === 501) {

      const allRows = [...newRowData];
      const newData: any = [];

      allRows.forEach((e, i) => {
        const newVal = _.cloneDeep(e);
        newVal.err = validateBuffer(e, activeMaster, bufferInitialData, bufferModifyData, bufferTypeData, allRows);
        newData.push(newVal);
      });

      dispatch(UPDATE_ROW_DATA(newData));
    }

    if (masterId === 502) {
      const allRows = [...newRowData];
      const newData: any = [];
      allRows.forEach((e: any, index: number) => {
        const newVal = _.cloneDeep(e);
        newVal.err = validateCCR(e, activeMaster, ccrInitialData, ccrModifyData, CCRGroupMaterSetRef, plantMaster, deptMaster);
        newData.push(newVal);
      });
      

      // Dispatch the updated row data
      dispatch(UPDATE_ROW_DATA(newData));
    }

    if (activeMaster.id === 503) {
      const allRows = [...newRowData];
      const newData: any = [];
      allRows.forEach((e: any) => {
        const newVal = _.cloneDeep(e);
        
        if (
          plantMaster.length &&
          !plantMaster.some(
            (plant: any) =>
              plant.plant_name === e.plnm || plant.plant_id === e.plnm
          )
        ) {
          newVal.err = {
            error: "Please select a valid plant from the dropdown",
            warning: "",
          };
        } else if (e.plnm === "" || !e.plnm) {
          newVal.err = { error: "Plant name cannot be empty!", warning: "" };
        }
        if (e.majdsc === "" || e.majdsc === null) {
          newVal.err = {
            error: "Major reason description cannot be empty!",
            warning: "",
          };
        } else if (e.mindsc === "" || e.mindsc === null) {
          newVal.err = {
            error: "Each major reason must have at least one minor reason!",
            warning: "",
          };
        }
        if (
          e.mindsc !== "" &&
          e.mindsc !== null &&
          (e.majdsc === "" || e.majdsc === null)
        ) {
          newVal.err = {
            error: "State the major reason to which the minor reason belongs!",
            warning: "",
          };
        }

        // Assuming newData is an array of objects and e is an object with majdsc and mindsc properties
        const isDuplicate = newData.some((item:any) => (
          item.majdsc === e.majdsc && item.mindsc === e.mindsc
        ));

        if (isDuplicate) {
          newVal.err = {
            error: "Minor reason should be unique for each major reason!",
            warning: ""
          };
        }

        newData.push(newVal);
      });

      dispatch(UPDATE_ROW_DATA(newData));
    }

    if(activeMaster.id === 504){
      const allRows = [...newRowData];
      const newData: any = [];

      allRows.forEach((e:any)=>{
        const newVal = _.cloneDeep(e);

        const {error} = CALENDAR_Add_VALIDATION_SCHEMA.validate(e,{abortEarly:false})

        if(error){
          const fieldOrders = activeMaster.fields.map(field =>field.key)

         const errorOrders = fieldOrders.flatMap((field:string)=>{
            return error.details.filter(err=> err.path[0] === field)
         })

         newVal.err = {
            error: errorOrders[0].message,
            warning: ""
          }

          newData.push(newVal)

        }else{

          newData.push(newVal)
        }
      })

      dispatch(UPDATE_ROW_DATA(newData));
    }
  };

  const sideBar: SideBarDef = {
    // toolPanels: [
    //   {
    //     id: "columns",
    //     labelDefault: "Columns",
    //     labelKey: "columns",
    //     iconKey: "columns",
    //     toolPanel: "agColumnsToolPanel",
    //     toolPanelParams: {
    //       suppressPivots: true,
    //       suppressRowGroups: true,
    //       suppressPivotMode: true,
    //       suppressValues: true
    //     },
    //   },
    // ],
    defaultToolPanel: defaultToolPanel,
  };

  const agGridProps: AgGridReactProps = {
    singleClickEdit:true,
    tooltipShowDelay: 0,
    readOnlyEdit: true,
    tooltipTrigger: "hover",
    sideBar: ["default", "view"].includes(activeMaster.progress) ? sideBar : {},
    gridOptions: {
      getRowStyle: (params: any) => {
        if (params.node.rowIndex % 2 === 0) {
          return { background: "#EBEBEB" };
        }
        return { background: "#F7F7F7" };
      },
    },
    pagination: true,
    paginationPageSize: rowsPerPage,
    // suppressPaginationPanel:true,
    onColumnVisible: onColumnChange,
    // overlayLoadingTemplate:'<object style="position:absolute;top:50%;left:50%;transform:translate(-50%, -50%) scale(2)" type="image/svg+xml" data="/assets/img/VectorFLOW/loaderMedium.svg" aria-label="loading"></object>',
    loadingOverlayComponent: "loadingOverlay",
    onFirstDataRendered: () => {
      if (pageType === "add") {
        const newRowData = _.cloneDeep(activeMaster.rowData);
        newRowData.forEach((ele: any) => {
          if (!ele.err || typeof ele.err === "string") {
            ele.err = { error: "" };
          } else {
            ele.err.error = "";
          }
        });
        validateMTOMaster(activeMaster.id, newRowData);
        return;
      }
    },
    onCellValueChanged: (event) => {
      const data = event.data;
      const field: any = event.colDef.field;
      const newValue = event.newValue;
      const newRow = { ...data };
      newRow[field] = newValue;
      // if(activeMaster.id===503){
      //   return;
      // }
      if (pageType === "add") {
        const newRowData = _.cloneDeep(
          activeMaster.rowData.map((row: any) => {
            if (JSON.stringify(row) === JSON.stringify(data)) {
              return newRow;
            }
            return row;
          })
        );
        newRowData.forEach((ele: any) => {
          if (typeof ele.err === "string") {
            ele.err = { error: "" };
          } else {
            ele.err.error = "";
          }
        });
        validateMTOMaster(activeMaster.id, newRowData);
        return;
      }
    },
    onRowDataUpdated: (event: any) => {
      if (activeMaster.id === 503) {
        const nodesToSelect: any = [];

        event.api.forEachNode((node: any) => {
          if (
            !node.data.minId &&
            node.data?.majId === selectedMajReason?.majId
          ) {
            nodesToSelect.push(node);
          }
        });
        event.api.setNodesSelected({ nodes: nodesToSelect, newValue: true });
      }

      const downloadableColumnKeys: string[] = [];
      activeMaster.fields.forEach((field: Field) => {
        if (field.isDownload) {
          downloadableColumnKeys.push(field.key);
        }
      });

      if (downloadData) {
        const currentMaster = masters.find(
          (master: MDMMasterState) => master.id === activeMaster.id
        );
        const visibleColumns = ref.current?.api.getAllDisplayedColumns();
        const validColumnKeys: string[] = [];
        if (visibleColumns) {
          visibleColumns.forEach((col: any) => {
            if (
              isUploadModalOpen &&
              !downloadableColumnKeys.includes(col.colId)
            ) {
              return;
            }
            validColumnKeys.push(col.colId);
          });
        }
        // if (currentMaster) {
        //   event.api.exportDataAsExcel(onExcelExprot(colDefs));
        // }
      }
    },
    rowSelection: "multiple",
    suppressRowClickSelection: true,
    components: customCellRenderers,
    onSelectionChanged: () => {
      if (ref.current?.api) {
        setSelectedRowsCount(ref.current?.api.getSelectedRows().length);
      }
    },
    onGridReady: (params: any) => {
      if (activeMaster.id === 501) {
        params.api.sizeColumnsToFit();
      }
    },

    onCellEditingStopped(event) {
      const data = event.data;
      const field: any = event.colDef.field;
      const newValue = event.newValue;
      const newRow = { ...data };
      newRow[field] = newValue;
      
      // if(activeMaster.id===503){
      //   return;
      // }
      if (pageType === "add") {
        const newRowData = _.cloneDeep(
          activeMaster.rowData.map((row: any) => {
            if (JSON.stringify(row) === JSON.stringify(data)) {
              return newRow;
            }
            return row;
          })
        );
        newRowData.forEach((ele: any) => {
          if (typeof ele.err === "string") {
            ele.err = { error: "" };
          } else {
            ele.err.error = "";
          }
        });
        validateMTOMaster(activeMaster.id, newRowData);
        return;
      }

      if (data.minId === undefined) {
        const newRowData = activeMaster.rowData.map((row: any) => {
          if (JSON.stringify(row) === JSON.stringify(data)) {
            return newRow;
          }
          return row;
        });
        // setEnableEditOnlineReset(true)
        dispatch(UPDATE_ROW_DATA([...newRowData]));
      } else if (activeMaster.id === 503) {
        const newRowData = activeMaster.rowData.map((row: any) => {
          if (JSON.stringify(row.majId) === JSON.stringify(data.majId)) {
            row.minData.map((ele: any) => {
              if (ele.minId === data.minId) {
                return data;
              }
              return ele;
            });
          }
          return row;
        });
        dispatch(UPDATE_ROW_DATA([...newRowData]));
      }
    },
    statusBar:{
      statusPanels: [
        {
          statusPanel: "agTotalAndFilteredRowCountComponent",
          align: 'left',
          
        },
        {
          statusPanel: CustomStatusPanel,
          key: 'clearGridFilters',
          align:'right',
          statusPanelParams: {
            isDisabled,
            clearGridFilter,
            themeUi,
          },
        },
        {
          statusPanel: "agTotalRowCountComponent",
          align: "left",
        },
        {
          statusPanel: "agFilteredRowCountComponent",
          align: "left",
        },
        {
          statusPanel: "agSelectedRowCountComponent",
          align: "left",
        },
        {
          statusPanel: "agAggregationComponent",
          align: "left",
        },
      ],
    },
    onFilterChanged:() => {
      if(ref && ref.current && ref.current.api){
        Object.keys(ref.current.api.getFilterModel())?.length > 0
          ? setIsDisabled(false)
          : setIsDisabled(true);
      }
    }
  };

  const getTempGridColDefs = () => {
    //check if it already contains
    let doesInvalidColDefExists = false;
    invalidDataColdefs.forEach((invalidColumn: ColDef) => {
      if (
        activeMaster.colDefs.find(
          (column: ColDef) => invalidColumn.colId === column.colId
        )
      )
        doesInvalidColDefExists = true;
    });
    if (doesInvalidColDefExists) return [...activeMaster.colDefs];
    return [...invalidDataColdefs, ...activeMaster.colDefs];
  };

  const tempAgGridProps: AgGridReactProps = {
    columnDefs: getTempGridColDefs(),
    onRowDataUpdated: (event) => {
      const Colparams: any = {
        columnKeys: activeMaster.colDefs
          .filter(
            (col: ColDef) =>
              col.headerName !== "Warning" && col.headerName !== "Error"
          )
          .map((col: ColDef) => col.field),
      };
      if (tempDownloadData)
        event.api.exportDataAsExcel({
          fileName: downloadFileName
            ? "Error-" + downloadFileName
            : "Error-" + activeMaster.name,
          columnKeys: Colparams.columnKeys,
        });
      // if (tempDownloadData) event.api.exportDataAsExcel({  fileName: downloadFileName ? 'Error-' + downloadFileName : 'Error-' + activeMaster.name});
    },
  };

  const addCheckBoxColDefs = () => {
    const checkboxColDefs: ColDef[] = [
      {
        field: "checkbox",
        colId: "checkbox",
        headerName: "",
        width: 40,
        checkboxSelection: true,
        headerCheckboxSelection: true,
        headerCheckboxSelectionCurrentPageOnly: true,
      },
      // {
      //   field:'checkbox',
      //   he
      //   headerName:'Select Across All Pages',
      //   // checkboxSelection:true,
      //   headerCheckboxSelection:true
      // },
    ];
    dispatch(ADD_COLDEFS({ colDefs: checkboxColDefs }));
    dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
  };

  const addInvalidDataColDefs = (columnName: string) => {
    dispatch(
      ADD_COLDEFS({
        colDefs: [
          columnName === "error"
            ? invalidDataColdefs[1]
            : invalidDataColdefs[0],
        ],
      })
    );
    // dispatch(SYNC_ACTIVE_MASTER_TO_MASTER())
  };

  const getCurrentVisbileColumns = () => {
    const columnData = ref.current?.api.getAllDisplayedColumns();
    return columnData?.map((column: any) => ({ key: column.colDef.field }));
  };

  function convertArrayToObject(
    input: { attributeName: string; op: string; value: string }[]
  ) {
    const operatorMap: Record<string, string> = {
      "=": "et",
      "!=": "net",
      ">": "gt",
      "<": "lt",
      ">=": "gte",
      "<=": "lte",
      contains: "cn",
      startsWith: "sw",
      endsWith: "ew",
      hasValue: "hv",
      hasNoValue: "dnc",
      // Add more mappings as needed
    };

    // 'lt': 'lt',
    //     'lte': 'lte',
    //     'gt': 'gt',
    //     'gte': 'gte',
    //     'sw': 'istartswith',
    //     'ew': 'iendswith',
    //     'et': 'exact',
    //     'cn': 'icontains',
    //     'dnc': 'donotcontains',
    //     'dsw': 'doesnotstartswith',
    //     'dew' : 'doesnotendswith',
    //     'hv' : 'hv',
    //     'net' : 'notequalto'

    return input.reduce((acc, { attributeName, op, value }) => {
      acc[attributeName] = {
        op: operatorMap[op] || op, // Convert operator or fallback to original
        val: value,
      };
      return acc;
    }, {} as Record<string, { op: string; val: string }>);
  }
  const queryFilteredData = async (configs: QueryFilteredDataConfigs) => {
    const newColDefs: any = [];
    activeMaster.colDefs.forEach((ele: any) => {
      const newColDef = { ...ele };
      delete newColDef.editable;
      newColDefs.push(newColDef);
    });

    dispatch(
      UPDATE_COLDEFS(newColDefs.filter((item: any) => item.field !== "actions"))
    );

    const { filters, pagination, fields, count, currentPage, rowsPerPage } =
      configs;
    const payload: GetMasterDataPayload = {
      id: activeMaster.id,
      name: activeMaster.name,
      filters: filters,
      fields: fields,
    };

    if (pagination && !count) {
      payload.paginationParameter = {
        pageNumber: currentPage,
        recordsPerPage: rowsPerPage,
      };
    }

    const finPayload: any = convertArrayToObject(filters);

    let resultData;

    if (finPayload.bt) finPayload.btype = finPayload.bt;
    delete finPayload.bt;
    if (finPayload.pl) finPayload.plnm = finPayload.pl;
    delete finPayload.pl;
    if (finPayload.dp) finPayload.dpnm = finPayload.dp;
    delete finPayload.dp;
    if (finPayload.cgid) finPayload.cg = finPayload.cgid;
    delete finPayload.cgid;
    /******  cb9a1de4-0e9b-4735-8968-a85fa557c44e  *******/

    if (activeMaster.id === 501) {
      const tempResultData = await getBufferMasterData({ finPayload });
      const updatedData = _.cloneDeep(tempResultData);
      if (bufferModifyData && bufferModifyData.length) {
        const updatedDataBuffer = updatedData.data.data;
        const filteredDataBuffer = updatedDataBuffer.filter(
          (buffer: any) =>
            !bufferModifyData.some(
              (modifiedBuffer: any) => modifiedBuffer.bid === buffer.bid
            )
        );
        updatedData.data.data = updatedData.data.data = [
          ...bufferModifyData,
          ...filteredDataBuffer,
        ];
      }
      resultData = updatedData;
    }
    if (activeMaster.id === 502) {
      const tempResultData = await getCCRMasterData({ finPayload });
      const updatedData = _.cloneDeep(tempResultData);
      if (ccrModifyData && ccrModifyData.length) {
        const updatedDataBuffer = updatedData.data.data;
        const filteredDataBuffer = updatedDataBuffer.filter(
          (buffer: any) =>
            !ccrModifyData.some(
              (modifiedBuffer: any) => modifiedBuffer.cid === buffer.cid
            )
        );
        updatedData.data.data = updatedData.data.data = [
          ...ccrModifyData,
          ...filteredDataBuffer,
        ];
      }
      resultData = updatedData;
    }
    if (activeMaster.id === 503) {
      const tempResultData = await getPOOGIMasterData({ finPayload });
      const updatedData = _.cloneDeep(tempResultData);
      if (poogiModifyData && poogiModifyData.length) {
        const updatedDataBuffer = updatedData.data.data;
        const filteredDataBuffer = updatedDataBuffer.filter(
          (buffer: any) =>
            !poogiModifyData.some(
              (modifiedBuffer: any) => modifiedBuffer.cid === buffer.cid
            )
        );
        updatedData.data.data = updatedData.data.data = [
          ...ccrModifyData,
          ...filteredDataBuffer,
        ];
      }
      resultData = updatedData;
    }

    return resultData;
  };
    
    // on saving a new calender or edit a calender
    const onSaveHandler = () => {
      const index = activeMaster.rowData?.length ? activeMaster.rowData?.findIndex((row) => row.hid === selectedData.hid) : -1;
        const rowData = _.cloneDeep(activeMaster.rowData || []);
        let newData = _.cloneDeep(selectedData);
        const {error} = CALENDAR_VALIDATION_SCHEMA.validate(selectedData,{abortEarly:false})

        if(error){
          const fieldOrders = activeMaster.colDefs.filter((item:any)=> item.headerName !== "Action").map((item:any)=> item.field);

          const orderedErrors = fieldOrders.flatMap((key: any) => (
            error.details.filter((err: any) => err.path[0] === key)
            
          ));

          notifyError(orderedErrors[0]?.message);


          // return notifyError(orderedErrors[0]?.message)
          
        }

        // edit calendar 
      if (index!=-1) { 
          if(newData.ia !== true){
            newData = {...newData,iu:true,id:false}
          }
          rowData[index] = newData
        }
        // add new calendar
        else{
          newData.ia = true
          newData = {...newData,iu:false,id:false,}
          rowData.unshift(newData);
        }

        dispatch(UPDATE_ROW_DATA(rowData))
        setIsModalOpen(false)
    }
  

    // on deleting a calendar from action
    const onDeleteHandler = (index: any, rowData:any) => {
      const newData = _.cloneDeep([...rowData])
      const currDeleteObj = {...newData[index]}
      if (index !== -1) {
        if(currDeleteObj.iu){
          currDeleteObj.iu = false
        }
        currDeleteObj.id = true
        currDeleteObj.iu = false
        newData[index] = currDeleteObj;
        dispatch(UPDATE_ROW_DATA(newData)); 
      }
    }

    const onDeleteUndoHandler = (index:number,rowData:any)=>{
      const newData = _.cloneDeep([...rowData])
      const currDeleteObj = {...newData[index]}
      if(index !== -1){
       currDeleteObj.id = !currDeleteObj.id;
       newData[index] = currDeleteObj
       dispatch(UPDATE_ROW_DATA(newData))
      }
    }
    

  const queryAllData = async (configs: QueryFilteredDataConfigs) => {
    const newColDefs: any = [];
    activeMaster.colDefs.forEach((ele: any) => {
      const newColDef = { ...ele };
      delete newColDef.editable;
      newColDefs.push(newColDef);
    });

    const { pagination, fields, count, currentPage, rowsPerPage } = configs;
    const payload: GetMasterDataPayload = {
      id: activeMaster.id,
      name: activeMaster.name,
      filters: [],
      fields: fields,
    };

    if (pagination && !count) {
      payload.paginationParameter = {
        pageNumber: currentPage,
        recordsPerPage: rowsPerPage,
      };
    }
    let resultData;
    if ((!activeMaster.isMTO && count) || activeMaster.isMTO) {
      if (activeMaster.id === 501) {
        const tempResultData = await getBufferMasterData({});
        const updatedData = _.cloneDeep(tempResultData);
        if (bufferModifyData && bufferModifyData.length) {
          const updatedDataBuffer = updatedData.data.data;
          const filteredDataBuffer = updatedDataBuffer.filter(
            (buffer: any) =>
              !bufferModifyData.some(
                (modifiedBuffer: any) => modifiedBuffer.bid === buffer.bid
              )
          );
          updatedData.data.data = updatedData.data.data = [
            ...bufferModifyData,
            ...filteredDataBuffer,
          ];
        }
        resultData = updatedData;
      } else if (activeMaster.id === 502 && activeMaster.isMTO) {
        const tempResultData = await getCCRMasterData({});
        const updatedData = _.cloneDeep(tempResultData);
        if (ccrModifyData && ccrModifyData.length) {
          const updatedDataBuffer = updatedData.data.data;
          const filteredDataBuffer = updatedDataBuffer.filter(
            (buffer: any) =>
              !ccrModifyData.some(
                (modifiedBuffer: any) => modifiedBuffer.cid === buffer.cid
              )
          );
          updatedData.data.data = [
            ...ccrModifyData,
            ...filteredDataBuffer,
          ];
        }
        resultData = updatedData;
      } else if (activeMaster.id === 503 && activeMaster.isMTO) {
        const tempResultData = await getPOOGIMasterData({});
        const updatedData = _.cloneDeep(tempResultData);
        if (poogiModifyData && poogiModifyData.length) {
          const updatedDataPoogi = updatedData.data.data;
          const filteredDataPoogi = updatedDataPoogi.filter(
            (poogi: any) =>
              !poogiModifyData.some(
                (modifiedPoogi: any) => modifiedPoogi.majId === poogi.majId
              )
          );
          updatedData.data.data = updatedData.data.data = [
            ...poogiModifyData,
            ...filteredDataPoogi,
          ];
        }
        resultData = updatedData;
      } else if (activeMaster.id === 504 && activeMaster.isMTO) {
        resultData = await getCalendarMasterData();
        if (
          !activeMaster.colDefs.some(
            (col: ColDef) => col.headerName === "Action"
          )
        ) {
          const newColDefs = [
            ...activeMaster.colDefs,
            {
              headerName: "Action",
              cellRenderer: MTOCalendarEditCellRenderer,
              cellRendererParams: {
                handleOpenClick: (index: number, data: any) => {
                  setIsModalOpen(true);
                  setCalendarFormData(data);
                },
                onDeleteUndoHandler,
                onDeleteHandler,
              },
              filter: false,
            },
          ];
          
          const finColDefs = newColDefs.map((col: any) => {
            if (col.field === "dow") {
              return {
                ...col,
                cellRenderer: DaysOfWeekRenderer,
              };
            }
            if( col.field === "ccr_id"){
              return {
                ...col,
                valueFormatter:(params:any)=>{
                  return getCCRNamesFromId(ccrsData,params?.data?.ccr_id) 
                }
              }
            }
            return col;
          });

         
          dispatch(UPDATE_COLDEFS(finColDefs))
        }
      }
    } else {
      if (activeMaster.id === 501 && activeMaster.isMTO) {
        resultData = await getBufferMasterData({});
      } else if (activeMaster.id === 502 && activeMaster.isMTO) {
        resultData = await getCCRMasterData({});
      } else if (activeMaster.id === 503 && activeMaster.isMTO) {
        resultData = await getPOOGIMasterData({});
        dispatch(SET_POOGI_INITIAL_DATA(resultData.data.data));
      } else if (activeMaster.id === 504 && activeMaster.isMTO) {
        resultData = await getCalendarMasterData();
      }
    }

    return resultData;
  };

  const handleSelectMasterSubmit = () => {
    masters.forEach((master: MDMMasterState) => {
      if (!master.isChecked) {
        dispatch(REMOVE_MASTER(master.id));
      }
    });
    if (activeMaster.id === 0) {
      dispatch(UPDATE_ACTIVE_MASTER(0));
    } else {
      dispatch(UPDATE_ACTIVE_MASTER(masters[0]));
    }
    dispatch(TOGGLE_SELECT_MASTER_SCREEN(false));
  };

  const handleTabChange = (currMaster: MDMMasterState) => {
    if (currMaster.progress === "submitted")
      return notifyError(`The ${currMaster.name} is already submitted`);
    
    // const nextMasterIndex = masters.findIndex(
    //   (master: MDMMasterState) =>
    //     master.progress !== "submitted" &&
    //     master.progress !== "editOnlineSubmitted"
    // );

    if(((bufferModifyData?.length===undefined || bufferModifyData?.length==0) && (ccrModifyData?.length===undefined || ccrModifyData?.length==0) && (poogiModifyData?.length===undefined || poogiModifyData?.length==0))){
      if (activeMaster.isMTO) {
        dispatch(UPDATE_ACTIVE_MASTER(currMaster));
        return;
      }
    }
    else return notifyError(`Please Complete the current Master`);  
  };

  const generateDraftPayload = (rowData: any, draftId?: string) => {
    const pathName = window.location.pathname.split("/");
    let instanceName = "";
    masters.map((master: MDMMasterState) => {
      instanceName += ` ${master.name}`;
    });
    return {
      instanceName: instanceName,
      searchKey: activeMaster.name,
      actionType: getActionId(pathName[pathName.length - 1]).id,
      draftId: draftId,
      draftData: masters.map((master: MDMMasterState) => {
        return {
          masterId: master.id,
          status: master.progress,
          gridState:
            master.id === activeMaster.id
              ? JSON.stringify(activeMaster.colDefs)
              : "",
          dataMaster: master.id === activeMaster.id ? rowData : [],
        };
      }),
    };
  };

  const handleTabClose = (
    e: React.MouseEvent<HTMLElement>,
    currMaster: MDMMasterState
  ) => {
    e.stopPropagation();
    if (masters.length === 1) {
      return notifyError("There Should be atleast one selected Master");
    }
    dispatch(REMOVE_MASTER(currMaster.id));
    setDownloadData(false);
    if (currMaster.id === activeMaster.id) {
      const mastersLength = masters.length;
      for (let index = 0; index < mastersLength; index++) {
        if (masters[index].progress !== "submitted") {
          dispatch(UPDATE_ACTIVE_MASTER(index));
          return;
        }
      }
    }
  };

  const addNewMaster = () => {
    if (allMastersState.length === masters.length) {
      notifyError(
        "All Masters have already been selected. Cannot add more masters"
      );
      return;
    }
    dispatch(TOGGLE_SELECT_MASTER_SCREEN(true));
    setDownloadData(false);
    setTempDownloadData(false);
  };

  const handleOnAddFilter = () => {
    dispatch(ADD_FILTER());
    dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
  };

  const handleOnDeleteFilter = (id: string) => {
    if (activeMaster.filters.length === 1) {
      // dispatch(REMOVE_FILTER(id));
      // dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
      dispatch(RESET_FILTERS());
      dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
      
      // dispatch(UPDATE_FILTER(emptyFilter))
      return;
      // return notifyError("Cannot Delete this Filter Instance")
    }
    
    dispatch(REMOVE_FILTER(id));
    dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
  };


  const handleApplyFilter = async (showAll?: boolean) => {
    if (showAll) setIsShowAll(showAll);
    else setIsShowAll(false);
    if (downloadData) setDownloadData(false);
    const currMasterFilters = activeMaster.filters;
    if (!areMasterFiltersValid(currMasterFilters) && !showAll) {
      return notifyError("Filter cannot be empty");
    }

    const payloadFilters = mapStateFiltersToPayload(currMasterFilters);
    const payloadFields: any = getCurrentVisbileColumns();

    setIsTableDataLoading(true);

    let result;
    try {
      if (showAll) {
        result = await queryAllData({
          filters: payloadFilters,
          fields: payloadFields,
          pagination: false,
          count: true,
          rowsPerPage,
        });
      } else {
        result = await queryFilteredData({
          filters: payloadFilters,
          fields: payloadFields,
          pagination: false,
          count: true,
          rowsPerPage,
        });
      }
    } catch (err) {
      console.error(err);
    }

    setIsTableDataLoading(false);
    if (activeMaster.isMTO) {
      if (
        !result?.data?.data?.count ||
        result?.data?.data?.count == 0 ||
        result?.data?.data?.count == ""
      ) {
        setTempRecordCount(result?.data?.data?.length);
      } else {
        setTempRecordCount(result?.data?.data?.count);
      }
    } 
  
    toggleWarningModal(true);
  };

  const onWarningModalClose = () => {
    toggleWarningModal(false);
    setIsTableDataLoading(false);
    setTempRecordCount(0);
  };

  const onWarningModalSuccess = async (refetch = false) => {
    try {
      setIsTableDataLoading(true);
  
      const { filters: currMasterFilters, colDefs } = activeMaster;
      const payloadFilters = mapStateFiltersToPayload(currMasterFilters);
      const payloadFields: any = getCurrentVisbileColumns()?.filter(
        (f: any) => !["checkbox", "graph", "color"].includes(f.key)
      );
  
      const shouldFetchAll =
        (!areMasterFiltersValid(currMasterFilters) && currMasterFilters.length === 1) ||
        isShowAll;
  
      const queryFn = shouldFetchAll ? queryAllData : queryFilteredData;
      const queryLabel = shouldFetchAll ? "All Data" : "Filtered Data";
  
      const result: any = await notifyPromise(
        queryFn({
          filters: payloadFilters,
          fields: payloadFields,
          pagination: true,
          currentPage: 1,
          rowsPerPage,
        }),
        {
          success: `${queryLabel} Fetched Successfully`,
          error: "Something Went Wrong",
          pending: "Loading Data...",
        }
      );
  
      // Reset filters only if we fetched all data
      if (shouldFetchAll) dispatch(RESET_FILTERS());
  
      const hasFewRecords = tempRecordCount <= rowsPerPage;
      dispatch(UPDATE_DATA_AVAILABILITY_STATUS(hasFewRecords));
      toggleEditOnline(hasFewRecords);
  
      if (tempRecordCount === 0) {
        toggleWarningModal(false);
        return;
      }
  
      const rawData = result?.data?.data ?? [];
      const tempRowData = rawData.map((row: any) => {
        const newRow = { ...row };
        Object.entries(newRow).forEach(([key, value]:any) => {
          const colDef = colDefs.find((c) => c.colId === key);
          if (colDef?.cellDataType === "number" && value !== null) {
            newRow[key] = parseFloat(value);
          }
        });
        return newRow;
      });
  
      dispatch(UPDATE_ROW_DATA(tempRowData));
  
      if (!refetch) {
        toggleWarningModal(false);
        dispatch(SET_RECORD_COUNT(tempRecordCount));
        dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
      }
    } catch (err) {
      console.error("Error in onWarningModalSuccess:", err);
    } finally {
      setIsTableDataLoading(false);
    }
  };
  
  
  const onUploadMaster = async () => {
    let intervalID: any;
    try {
      if (!file) {
        notifyError("Please select a file to upload.");
        return;
      }
      // const selectedColumns = ref.current?.api.getAllDisplayedColumns();
      // const toasId = notifyLoader("Reading File");
      setIsOverlayVisible(true);

      // TODO : MTO check for which all master this needs to be done
      const buffData = await parseMTOExcelData(
        file,
        activeMaster,
        pageType
      );

      if (activeMaster.id === 501) {
        buffData.forEach((bufferType: any) => {
          const match = bufferTypeData.find((bufferTypeData: any) => bufferTypeData.nm === bufferType.bt);
          if (match) {
            bufferType.bt = match.id;
          }
        });
      }
      
      getInitialData();

      const updatedColdefs = getUpdatedColDefs({
        colDefs: activeMaster.colDefs,
        activeMaster,
        bufferTypeData,
        ToggleButton,
        plantMaster,
        deptMaster,
        ccrGroupMaster,
        ccr_names,
        mode: "upload",
      });

      /////
      // const updatedColdefs:any = activeMaster?.colDefs?.map((col: ColDef) => {
      //   // const isEditable = activeMaster.fields.find((field: Field) => field.key === col.colId)?.isEdit;
      //   if (col.field === "iv") return { ...col, cellRenderer: ToggleButton, pinned: 'right', filter: false };
      //   if (col.field === "bt")
      //     return {
      //       ...col,
      //       editable: true,
      //       cellEditor: "agRichSelectCellEditor",
      //       cellEditorParams: {
      //         values: bufferTypeData?.map((item: any) => item.id),
      //         formatValue: (id: any) => getCategoryName(id)
      //       },
      //       valueGetter: (params: any) => {
      //         return getCategoryName(params?.data?.bt)
      //       },
      //       filter: 'agTextColumnFilter',
      //     }
      //   if (col.field === "pl" || col.field === "plnm" || col.field ==='pid')
      //     return {
      //       ...col,
      //       editable: true,
      //       cellEditor: "agRichSelectCellEditor",
      //       cellEditorParams: {
      //         values: plantMaster?.map((item: any) => item.plant_name),
      //       },
      //     };
      
        
      //   if(col.field === "ccrId"){
      //     return {
      //       ...col,
      //       editable: true,
      //       cellEditor: "agRichSelectCellEditor",
      //       cellEditorParams:{
      //         values: ccr_names?.map((ccr: string) => ccr),
      //       }
      //     }
      //   }

      //   if (col.field === "sd" || col.field === "ed") {
      //     return {
      //       ...col,
      //       cellDataType:'date',
      //       editable: true,
      //       cellEditor:"agDateCellEditor",
      //       valueFormatter: (params: any) => {
      //         if(params.value === null || params.value === undefined) return '';
      //         const date = new Date(params.value);
      //         return date.toLocaleDateString("en-CA");

      //       },
      //       // cellRenderer: DueDateCellRenderer,
      //     };
      //   }

      //   if (col.field === "dp")
      //     return {
      //       ...col,
      //       editable: true,
      //       cellEditor: "agRichSelectCellEditor",
      //       cellEditorParams: {
      //         values: deptMaster?.map((item: any) => item.dept_name),
      //       },
      //     };

      //   if (col.field === "cgid")
      //     return {
      //       ...col,
      //       editable: true,
      //       cellEditor: "agRichSelectCellEditor",
      //       cellEditorParams: {
      //         values: Object.keys(ccrGroupMaster || {}),
      //       },
      //     };
      //   if (col.field === "slt")
      //     return {
      //       ...col,
      //       editable: true,
      //       cellEditor: "agNumberCellEditor",
      //     };
      //   if (col.field === "mlt")
      //     return {
      //       ...col,
      //       editable: true,
      //       cellEditor: "agNumberCellEditor",
      //     };
      //   if (col.field === "cpd")
      //     return {
      //       ...col,
      //       editable: true,
      //       cellEditor: "agNumberCellEditor",
      //     };
      //   if (col.field === "whpd")
      //     return {
      //       ...col,
      //       editable: true,
      //       cellEditor: "agNumberCellEditor",
      //     };
      //   if (col.field === "sh")
      //     return {
      //       ...col,
      //       editable: true,
      //       cellEditor: "agNumberCellEditor",
      //     };
      //   if (col.field === "rb")
      //     return {
      //       ...col,
      //       editable: true,
      //       cellEditor: "agNumberCellEditor",
      //     };
      //   if (col.field === "fh")
      //     return {
      //       ...col,
      //       editable: true,
      //       cellEditor: "agNumberCellEditor",
      //     };
      //   if (col.field === "cwl")
      //     return {
      //       ...col,
      //       editable: true,
      //       cellEditor: "agNumberCellEditor",
      //     };
      //   else return { ...col, editable: true, singleClickEdit: true };
      //   // return { ...col }
      // })

      dispatch(
        UPDATE_COLDEFS([
          {
            colId: "err",
            field: "err",
            cellRenderer: MTOErrorWarningCell,
            minWidth: 300,
            headerName: "Error",
            pinned: "left",
          },
          ...updatedColdefs,
        ])
      );
      
      ////
      const formData = new FormData();
      formData.append("file", file);
      formData.append("ui_config", JSON.stringify(activeMaster.fields));
      formData.append("screen_type", JSON.stringify({ screenType: pageType }));
      // const processId = uuidv4();

      // TODO: checked for buffer only make it dynamic
      //   if(activeMaster.id!==501 && activeMaster.id!==502 && activeMaster.id!==503 && activeMaster.id!==504){

      //     intervalID = setInterval(async () => {
      //       const progress = await getUploadProgress(processId);
      //       setUploadProgress(progress.data.progress);
      //       setTotalProgress(progress.data.totalRows)
      //     }, 1000)

      //     const response = await validateMaster({ formData, masterId: activeMaster.id });
      //     clearInterval(intervalID);
      //     let result = JSON.parse(response.data)
      //     const errorAndWarningData = result.filter((data: any) => data.error.length > 0 || data.warning.length > 0)
      //     result = [...errorAndWarningData, ...result.filter((data: any) => data.error.length === 0 && data.warning.length === 0)]

      //     setIsOverlayVisible(false);

      //   const ifErrorExists = result.find((data: any) => data.error.length > 1);
      //   const ifWarningExists = result.find((data: any) => data.warning.length > 1);

      //   if (ifErrorExists) {
      //     dispatch(UPDATE_PROGRESS_STATE('error'));
      //     addInvalidDataColDefs('error');
      //   }
      //   if (ifWarningExists) {
      //     // dispatch(UPDATE_PROGRESS_STATE('error'));
      //     addInvalidDataColDefs('warning');
      //   }
      //   if (!ifErrorExists) {
      //     if (activeMaster.progress === 'deleteView') dispatch(UPDATE_PROGRESS_STATE('deleteUploaded'));
      //     else dispatch(UPDATE_PROGRESS_STATE('uploaded'));
      //     addCheckBoxColDefs();
      //   }

      //   dispatch(SET_RECORD_COUNT(result.length));
      //   dispatch(UPDATE_ROW_DATA(result));
      //   dispatch(UPDATE_DATA_AVAILABILITY_STATUS(true));
      // }
      // else{
      dispatch(SET_RECORD_COUNT(buffData?.length));
      dispatch(UPDATE_DATA_AVAILABILITY_STATUS(true));

      dispatch(UPDATE_ROW_DATA(buffData));

      // }

      dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
      dispatch(TOGGLE_UPLOAD_MODAL(false));
      setIsOverlayVisible(false);
      notifySuccess(`Data Uploaded Successfully`);
      setDownloadData(false);
      setTempDownloadData(false);
      setCurrentPage(1);
    } catch (error: any) {
      toast.dismiss();
      notifyError(error.message);
      setIsOverlayVisible(false);
      if (intervalID) clearInterval(intervalID);
    }
  };

  const exportToExcel = async (fromUploadModal?: boolean) => {
    try {
      const currMasterFilters = activeMaster?.filters;
      const payloadFilters = areMasterFiltersValid(currMasterFilters)
        ? mapStateFiltersToPayload(currMasterFilters)
        : [];

      const payloadFields: any = getCurrentVisbileColumns();

      const numberOfPages = Math.ceil(recordCount / chunkSize);
      const toastId = notifyLoader(`Downloading Data 0 / ${recordCount}`);
      const rows = [];
      for (let i = 1; i <= numberOfPages; i++) {
        const result = await queryFilteredData({
          filters: payloadFilters,
          fields: payloadFields,
          showAll: false,
          pagination: true,
          currentPage: i,
          rowsPerPage: chunkSize,
        });
        if (result?.data.data === null) throw new Error("Something Went Wrong");
        if (result?.data) {
          rows.push(...result.data.data);
        }
        if (i === numberOfPages)
          toast.update(toastId, {
            render: `Downloading Data ${recordCount} / ${recordCount}`,
          });
        else
          toast.update(toastId, {
            render: `Downloading Data ${i * chunkSize} / ${recordCount}`,
          });
      }
      // dispatch(UPDATE_ROW_DATA(rows));
      dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
      setDownloadData(true);
      toast.dismiss(toastId);
      if (fromUploadModal) {
        setIsUploadButtonDisabled(false);
        notifySuccess(`Data Downloaded Successfully`);
        return;
      }

      notifySuccess(`Data Exported Successfully`);
    } catch (error) {
      toast.dismiss();
      notifyError("Something Went Wrong");
    }
  };

  const onClearExportError = () => {
    const erroneusData: any[] = [];
    const validData: any[] = [];
    activeMaster.rowData.forEach((data: any) => {
      if (data.err.error.length > 0) {
        erroneusData.push(data);
      } else {
        validData.push(data);
      }
    });
    setTempGridData(erroneusData);
    setTempDownloadData(true);

    // if(activeMaster.progress!=='submitted'){
    dispatch(UPDATE_ROW_DATA(validData));

    // dispatch(REMOVE_COLDEFS(['error','warning']));
    // addCheckBoxColDefs();
    // if(pageType==='remove') dispatch(UPDATE_PROGRESS_STATE('deleteUploaded'));
    // else  dispatch(UPDATE_PROGRESS_STATE('uploaded'));
    dispatch(SET_RECORD_COUNT(validData.length));
    dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
    // }
  };

  const deleteSelected = () => {
    const selectedRows = ref.current?.api.getSelectedRows();
    if (selectedRows && selectedRows.length > 0) {
      dispatch(REMOVE_ROW_DATA(selectedRows));
      dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
      notifySuccess(`${selectedRows?.length} records deleted successfully`);
      setSelectedRowsCount(0);
      dispatch(SET_RECORD_COUNT(recordCount - selectedRows.length));
    } else {
      notifyError("Please Select Rows to Delete");
    }
  };

  const onExcelExport = useMemo(()=>(
    (columnDefs = colDefs,buffTypeData = bufferTypeData,plantData = plantNames,deptData = deptMaster,ccrGroupData = ccrGroupMaster )=>{
      const isBufferExport = activeMaster.id === 501;
      const isCCRExport = activeMaster.id === 502;

      const bufferType = (value: any) => {
        return buffTypeData?.find((type: any) => type.id === value)?.nm;
      };
  
      const plantNameFromId = (value:any)=>{
        return plantData.find((plant:any)=> plant.plant_id === value)?.plant_name
      }
  
      const deptNameFromId = (value:any)=>{
        return deptData.find((dept:any)=> dept.dept_id === value)?.dept_name
      }
  
      const ccrGroupNameFromId = (value:any)=>{
        for(const key in ccrGroupData){
          if(ccrGroupData[key]?.ccr_group_id === value){
            return key
          }
        }
        return null
      }
      return {
        fileName : `${activeMaster.name} MTO`,
        columnKeys: columnDefs
          .filter((col: any) => col.field !== 'actions' && col.field !== 'err' && col.field !== 'iv') 
          .map((col: any) => col.field),             
        processCellCallback: (params: any) => {
          const { column, value } = params;
      
          if (isBufferExport && column.getColId() === 'bt') {
            const match = bufferType(value);
            return match ? match : value;  
          }
  
          if(isCCRExport && column.getColId() === 'pl'){
            const match = plantNameFromId(value)
            return match ? match : value
          }
  
          if(isCCRExport && column.getColId() === 'dp'){
            const match = deptNameFromId(value)
            return match ? match : value
          }
  
          if(isCCRExport && column.getColId() === 'cgid'){
            const match = ccrGroupNameFromId(value)
            return match ? match : value
          }
      
          return value?.toString() || "";       
        },
      
        processHeaderCallback: (params: any) => {
          const { column } = params;
          return column.getColDef().headerName || column.getColId();
        }
      };
    }
  ),[deptMaster,plantNames,ccrGroupMaster,ref,bufferTypeData,activeMaster?.id,activeMaster])
  

  const handleChangePage = async (pageNo: any) => {
    setCurrentPage(pageNo);
    setIsTableDataLoading(true);
    if (activeMaster.rowData.length > rowsPerPage) {
      ref.current?.api.paginationGoToPage(pageNo - 1);
      setIsTableDataLoading(false);
      return;
    }

    const payloadFilters = mapStateFiltersToPayload(activeMaster.filters);
    const payloadFields: any = getCurrentVisbileColumns();
    let result;
    if (
      !areMasterFiltersValid(activeMaster.filters) &&
      activeMaster.filters.length === 1
    ) {
      result = await queryAllData({
        filters: payloadFilters,
        fields: payloadFields,
        pagination: true,
        currentPage: pageNo,
        rowsPerPage,
      });
    } else {
      result = await queryFilteredData({
        filters: payloadFilters,
        fields: payloadFields,
        pagination: true,
        currentPage: pageNo,
        rowsPerPage,
      });
    }

    dispatch(UPDATE_ROW_DATA(result?.data.data));
    dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
    setIsTableDataLoading(false);
  };

  const postMasterDataChunks = async (
    rowData: any,
    isOverWrite?: boolean,
    actionStatus = ""
  ) => {
    const columnsToOmit = activeMaster.fields
      .filter((field: Field) => !field.isDownload)
      .map((field: Field) => field.key);
    if ([6].includes(parseInt(String(activeMaster.id), 10)) === false) {
      //CleanUp Row Data
      rowData = rowData.map((row: any) =>
        _.omit(row, "error", "warning", "users", columnsToOmit)
      );
    }

    // Convert To String
    rowData = rowData.map((row: any) => {
      const tempRow: any = {};
      Object.keys(row).forEach((key: string) => {
        if (row[key] === undefined || row[key] === null) {
          tempRow[key] = "";
        } else {
          tempRow[key] = row[key].toString();
        }
      });
      return tempRow;
    });
    let taskId: any = "";
    let toastId: any = "";
    let conflictCount = 0;
    let errorCount = 0;
    const tempConflictData: any = [];
    const errorData: any = [];
    try {
      let submitProgress = 0;
      const payload: any = {
        id: activeMaster.id,
        action: actionStatus,
        TaskId: "",
        IsOverWrite: isOverWrite === true ? true : false,
        data: [],
        uiconfig: activeMaster.fields,
      };

      toastId = notifyLoader(
        `Submitting Data ${submitProgress}/${activeMaster.rowData.length}`
      );

      for (let i = 0; i < rowData.length; i += chunkSize) {
        if (i + chunkSize < rowData.length) {
          payload.data = rowData.slice(i, i + chunkSize);
          toast.update(toastId, {
            render: `Submitting Data ${i + chunkSize}/${rowData.length}`,
          });
          submitProgress += chunkSize;
        } else {
          payload.data = rowData.slice(i);
          toast.update(toastId, {
            render: `Submitting Data ${rowData.length}/${rowData.length}`,
          });
        }

        let data: any;

        if (activeMaster.id > 14) {
          data = await modifyMasterRetail(payload);
        } else {
          data = await modifyMaster(payload);
        }

        if (taskId === "" && i !== 0) throw new Error("Something Went Wrong");

        if (TASK_ID === "") {
          payload.TaskId = data.data.taskId;
          taskId = data.data.taskId;
        } else {
          payload.TaskId = TASK_ID;
          taskId = TASK_ID;
        }

        setTaskId(data.data.taskId);

        if (data.data.conflictErrorCount) {
          conflictCount += parseInt(data.data.conflictErrorCount, 10);
        }
        errorCount += parseInt(data.data.errorCount, 10);
        const conflictedRows = data.data.conflictError;
        const errorenousRows = data.data.error;

        if (conflictedRows instanceof Array) {
          conflictedRows.forEach((row: any) => {
            const userIndex = tempConflictData.findIndex(
              (data: any) => data.user === row.user
            );
            if (userIndex >= 0) {
              tempConflictData[userIndex].conflictdetails = [
                ...tempConflictData[userIndex].conflictdetails,
                ...row.conflictdetails,
              ];
            } else {
              tempConflictData.push({
                user: row.user,
                conflictdetails: row.conflictdetails,
              });
            }
          });
        }
        if (errorenousRows instanceof Array) {
          errorenousRows.forEach((row: any) => {
            const userIndex = errorData.findIndex(
              (data: any) => data.errorType === row.errorType
            );
            if (userIndex >= 0) {
              errorData[userIndex].errorData = [
                ...errorData[userIndex].errorData,
                ...row.errorData,
              ];
            } else {
              errorData.push({
                errorType: row.errorType,
                errorData: row.errorData,
              });
            }
          });
        }
      }

      const intersectionCount =
        conflictCount + errorCount - activeMaster.rowData.length;

      const pureErrorCount =
        activeMaster.rowData.length + intersectionCount - conflictCount;
      const pureConflictCount =
        activeMaster.rowData.length + intersectionCount - errorCount;

      toast.dismiss(toastId);
      setConflictCount(pureConflictCount);
      setErrorCount(pureErrorCount);
      setConflictData(tempConflictData);
      setErrorData(errorData);
     
      return {
        isConflicts: pureConflictCount > 0,
        errorCount: pureErrorCount,
        errorData,
        conflictCount: pureConflictCount,
        conflictData: tempConflictData,
      };
    } catch (error) {
      notifyError("Something Went Wrong");
      if (taskId.length > 0) {
        await deleteTask(taskId);
      }
      toast.dismiss(toastId);
      return {
        isConflicts: true,
        errorCount,
        errorData,
        conflictCount,
        conflictData,
      };
    }
  };

  const onSubmit = async (isOverWrite?: boolean) => {
    if (activeMaster.rowData.length === 0) {
      notifyError("No Data to Submit");
      return;
    }

    setIsSubmitDisabled(true);

    if (isSubmitDisabled) return;

    if (activeMaster.progress === "editOnline") {
      //remove Editable Coldefs
      const updatedColdefs = activeMaster.colDefs.map((col: ColDef) => {
        return { ...col, editable: false };
      });
      dispatch(UPDATE_COLDEFS(updatedColdefs));
      // dispatch(REMOVE_COLDEFS(['error','warning']))
    }

    //check if errorneous Data
    const errorData = activeMaster.rowData.find((row: any) => {
      return (
        (row.error || row.warning) && (row.error !== "" || row.warning !== "")
      );
    });
    if (errorData) {
      notifyError("Please Clear Errors Before Submitting");
      return;
    }

    dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());

    dispatch(REMOVE_COLDEFS(["checkbox"]));
    //let result;

    if (activeMaster.progress === "editOnline") {
      const {
        isConflicts,
        errorCount: localErrorCount,
        errorData: localErrorData,
        conflictData: localConflictData,
      } = await postMasterDataChunks(activeMaster.rowData, isOverWrite);
      //result = !isConflicts
      if (!isConflicts) {
        if (localErrorCount > 0 || errorCount > 0) {
          let errorRowData;
          if (localErrorCount > 0) {
            errorRowData = createErrorRowData(localErrorData, activeMaster.id);
          } else {
            errorRowData = createErrorRowData(errorData, activeMaster.id);
          }
          if (!activeMaster.colDefs.find((c: ColDef) => c.colId === "error")) {
            addInvalidDataColDefs("error");
          }
          if (errorRowData.length > 0) {
            dispatch(UPDATE_ROW_DATA(errorRowData));
            dispatch(SET_RECORD_COUNT(errorRowData.length));
          }
        }
        notifySuccess(`Modifications Submitted Successfully`);
        setSelectedRowsCount(0);
        dispatch(UPDATE_PROGRESS_STATE("editOnlineSubmitted"));
        dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
        if (draftID.length > 0 && localErrorCount === 0) {
          await deleteDraft(draftID);
        }
      } else {
        const tempCon = createConflictRowData(
          localConflictData,
          activeMaster.id
        );
        const tempError = createErrorRowData(localErrorData, activeMaster.id);
        const tempResult: any = [];

        tempCon.forEach((t: any) => {
          const exist = tempError.find((e: any) => e.sc === t.sc);
          if (exist) tempResult.push(exist);
        });

       
        setConflictData(tempCon);
        setConflictCount(tempCon.length);
        setSubmittedDataCount(
          activeMaster.rowData.length -
            (tempCon.length -
              tempResult.length +
              (tempError.length - tempResult.length))
        );
        setIsConflictModalOpen(true);
        dispatch(UPDATE_PROGRESS_STATE("editOnlineConflicts"));
      }
    } else {
      const {
        isConflicts,
        errorCount: localErrorCount,
        errorData: localErrorData,
        conflictData: localConflictData,
      } = await postMasterDataChunks(activeMaster.rowData, isOverWrite);

      if (!isConflicts) {
        if (localErrorCount > 0 || errorCount > 0) {
          let errorRowData;
          if (localErrorCount > 0) {
            errorRowData = createErrorRowData(localErrorData, activeMaster.id);
          } else {
            errorRowData = createErrorRowData(errorData, activeMaster.id);
          }
          if (!activeMaster.colDefs.find((c: ColDef) => c.colId === "error")) {
            addInvalidDataColDefs("error");
          }
          if (errorRowData.length > 0) {
            dispatch(UPDATE_ROW_DATA(errorRowData));
            dispatch(SET_RECORD_COUNT(errorRowData.length));
          }
        }

        notifySuccess(`Modifications Submitted Successfully`);
        setSelectedRowsCount(0);
        dispatch(UPDATE_PROGRESS_STATE("submitted"));
        dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
        if (draftID.length > 0 && localErrorCount === 0) {
          await deleteDraft(draftID);
        }
      } else {

        const tempCon = createConflictRowData(
          localConflictData,
          activeMaster.id
        );
        const tempError = createErrorRowData(localErrorData, activeMaster.id);

        const tempResult: any = [];

        tempCon.forEach((t: any) => {
          const exist = tempError.find((e: any) => e.sc === t.sc);
          if (exist) tempResult.push(exist);
        });

        
        setConflictData(tempCon);
        setConflictCount(tempCon.length);
        setSubmittedDataCount(
          activeMaster.rowData.length -
            (tempCon.length -
              tempResult.length +
              (tempError.length - tempResult.length))
        );
        setIsConflictModalOpen(true);
        dispatch(UPDATE_PROGRESS_STATE("conflicts"));
      }
    }
    setIsSubmitDisabled(false);
  };

  const onPIPOStatusUpdate = async () => {
    const selectedRows = ref.current?.api.getSelectedRows();
    await postMasterDataChunks(selectedRows, false, "stop");
    onWarningModalSuccess(true);
    notifySuccess("Status Updated Successfully");
  };

  const resetMtoMasters = () => {
    dispatch(UPDATE_PROGRESS_STATE("default"));
    dispatch(UPDATE_ROW_DATA([]));
    dispatch(SET_BUFFER_INITIAL_DATA([]));
    dispatch(SET_BUFFER_MODIFY_DATA([]));
    dispatch(SET_CCR_INITIAL_DATA([]));
    dispatch(SET_CCR_MODIFY_DATA([]));
    dispatch(UPDATE_COLDEFS([]));
    dispatch(REMOVE_ALL_FILTERS());
    // dispatch(UPDATE_ACTIVE_MASTER([]))

    dispatch(ADD_FILTER());
    setDownloadData(false);
    setTempDownloadData(false);
    dispatch(FILL_MASTERS([]));
    setFilterButtonStatus([]);
    dispatch(TOGGLE_SELECT_MASTER_SCREEN(true));

    if (pageType === "add") dispatch(TOGGLE_UPLOAD_MODAL(true));

    dispatch(RESET_MTO_STATE());
    dispatch(UPDATE_PROGRESS_STATE("default"));
    dispatch(UPDATE_ROW_DATA([]));
    dispatch(SET_BUFFER_INITIAL_DATA([]));
    dispatch(SET_BUFFER_MODIFY_DATA([]));
    dispatch(UPDATE_COLDEFS([]));
    dispatch(REMOVE_ALL_FILTERS());
    dispatch(SET_CCR_INITIAL_DATA([]));
    dispatch(SET_CCR_MODIFY_DATA([]));
    // dispatch(UPDATE_ACTIVE_MASTER([]))

    dispatch(ADD_FILTER());
    setDownloadData(false);
    setTempDownloadData(false);
    dispatch(FILL_MASTERS([]));
    setFilterButtonStatus([]);
    dispatch(TOGGLE_SELECT_MASTER_SCREEN(true));

    if (pageType === "add") dispatch(TOGGLE_UPLOAD_MODAL(true));
  };

  const onBackButton = () => {
    
    const clearAllStates = () => {
      dispatch(RESET_STATE());
      dispatch(RESET_MTO_STATE());
      dispatch(UPDATE_PROGRESS_STATE("default"));
      dispatch(UPDATE_ROW_DATA([]));
      dispatch(SET_BUFFER_INITIAL_DATA([]));
      dispatch(SET_BUFFER_MODIFY_DATA([]));
      dispatch(UPDATE_COLDEFS([]));
      dispatch(REMOVE_ALL_FILTERS());
      dispatch(SET_CCR_INITIAL_DATA([]));
      dispatch(SET_CCR_MODIFY_DATA([]));
      // dispatch(UPDATE_ACTIVE_MASTER([])); // Uncomment if needed
      dispatch(ADD_FILTER());
      dispatch(FILL_MASTERS([]));
      dispatch(TOGGLE_SELECT_MASTER_SCREEN(true));
      
      setDownloadData(false);
      setTempDownloadData(false);
      setFilterButtonStatus([]);
      
      dispatch(RESET_MTO_STATE());
      
      // dispatch(REMOVE_MASTER(activeMaster.id));
      // const initMaster:any = {id:0,fields:[],filters:[],progress:'default',name:'',colDefs:[],rowData:[],isChecked:true}
      // dispatch(UPDATE_ACTIVE_MASTER(store.getState.));

  
      if (pageType === "add") {
        dispatch(TOGGLE_UPLOAD_MODAL(true));
      }
  
      if (backUrl) {
        navigate(backUrl);
      }
    };
  
    const hasUnsavedData = activeMaster?.rowData?.length;
  
    if (hasUnsavedData) {
      // const confirmed = confirm(
      //   "Are you sure you want to go back? All progress will be lost! Please Save to Draft."
      // );
      const confirmed = confirm(
        "Are you sure you want to go back? All progress will be lost!"
      );
      if (!confirmed) return;
    }
  
    clearAllStates();
  }  

  const postDraftChunks = async (rowData: any) => {
    let draftId = "";
    let chunkProgress = 0;
    let toastId;

    // Convert To String
    rowData = rowData.map((row: any) => {
      const tempRow: any = {};
      Object.keys(row).forEach((key: string) => {
        if (row[key] === undefined || row[key] === null) {
          tempRow[key] = "";
        } else {
          tempRow[key] = row[key].toString();
        }
      });
      return tempRow;
    });

    try {
      toastId = notifyLoader(
        `Creating Draft ${chunkProgress}/${activeMaster.rowData.length}`
      );
      for (let i = 0; i < rowData.length; i += chunkSize) {
        if (draftId.length > 0) {
          if (i + chunkSize < rowData.length) {
            await createDraft(
              generateDraftPayload(rowData.slice(i, i + chunkSize), draftId)
            );
            toast.update(toastId, {
              render: `Uploading ${i + chunkSize}/${rowData.length}`,
            });
            chunkProgress += chunkSize;
          } else {
            await createDraft(generateDraftPayload(rowData.slice(i), draftId));
            toast.update(toastId, {
              render: `Uploading ${rowData.length}/${rowData.length}`,
            });
          }
        } else {
          let data: any;
          if (draftID) {
            data = await modifyDraft(
              generateDraftPayload(rowData.slice(0, chunkSize), draftID)
            );
          } else {
            data = await createDraft(
              generateDraftPayload(rowData.slice(0, chunkSize))
            );
          }
          draftId = data.data.data;
          dispatch(SET_DRAFT_ID(data.data.data));
        }
      }
      toast.dismiss(toastId);
      return true;
    } catch (error) {
      if (draftId.length > 0 && draftID.length === 0) {
        await deleteDraft(draftId);
      }
      toast.dismiss(toastId);
      return false;
    }
  };

  const onSaveToDraft = async () => {
    let newData: any = [];
    const errorOrWarning = activeMaster.rowData.find(
      (row: any) =>
        Object.keys(row).includes("error") ||
        Object.keys(row).includes("warning")
    );
    if (errorOrWarning) {
      newData = activeMaster.rowData.map((row: any) => {
        const temp = { ...row };
        if (!temp["error"]) {
          temp["error"] = "";
        }
        if (!temp["warning"]) {
          temp["warning"] = "";
        }
        return temp;
      });
    } else {
      newData = activeMaster.rowData;
    }

    const selectedData = ref.current?.api.getSelectedRows();

    if (activeMaster.id == 10 || activeMaster.id == 6) {
      newData = newData.map((row: any) => {
        const tempRow = { ...row };
        if (
          selectedData?.find(
            (selectedRow: any) =>
              JSON.stringify(selectedRow) === JSON.stringify(row)
          )
        ) {
          tempRow.IsSelected = true;
          return tempRow;
        }
        tempRow.IsSelected = false;
        return tempRow;
      });
    }

    const res = await postDraftChunks(newData);
    if (res) {
      if (draftID.length > 0) {
        return notifySuccess("Draft Updated Successfully");
      } else {
        return notifySuccess("Draft Created Successfully");
      }
    }
    notifyError("Something Went Wrong");
    return false;
  };

  const onEditOnline = (progress: any) => {
    const updatedColdefs = activeMaster.colDefs.map((col: ColDef) => {
      const isEditable = activeMaster.fields.find(
        (field: Field) => field.key === col.colId
      )?.isEdit;

      if (isEditable) return { ...col, editable: true };
      return { ...col };
    });

    dispatch(UPDATE_PROGRESS_STATE(progress));
    dispatch(UPDATE_COLDEFS(updatedColdefs));
    dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());
  };

  const onReset = () => {
    const currentMasterData = masters.find(
      (master: MDMMasterState) => master.id === activeMaster.id
    );
    if (currentMasterData) dispatch(UPDATE_ROW_DATA(currentMasterData.rowData));
    dispatch(REMOVE_COLDEFS(["error", "warning"]));
    dispatch(UPDATE_PROGRESS_STATE("editOnline"));
    setEnableEditOnlineReset(false);
  };

  const getBufferMasterDataType = async () => {
    const BufferTypeMaster = await GetBufferTypeMaster();
    setBufferTypeData(BufferTypeMaster?.data?.data);
  };

  const onEditOnlineSave = async () => {
    await onSaveToDraft();
  };

  const toggleUploadModal = (value: boolean) => {
    dispatch(TOGGLE_UPLOAD_MODAL(value));
  };

  const onReviewConflicts = () => {
    const newColDefs: ColDef[] = activeMaster.colDefs.map((colDef: ColDef) => {
      return {
        ...colDef,
        cellRenderer: "conflictErrorCellRenderer",
        cellStyle: (params) => {
          return {
            ...params.colDef.cellStyle,
            padding: 0,
          };
        },
        // tooltipField:colDef.field
      };
    });

    if (newColDefs) dispatch(UPDATE_COLDEFS(newColDefs));
    addCheckBoxColDefs();
    dispatch(UPDATE_ROW_DATA(conflictData));
    setIsConflictModalOpen(false);
    dispatch(SET_RECORD_COUNT(conflictData.length));
  };

  const onIgnoreSubmitErrors = () => {
    const errorRowData = createErrorRowData(errorData, activeMaster.id);
    if (errorRowData.length > 0) {
      addInvalidDataColDefs("error");
      dispatch(UPDATE_ROW_DATA(errorRowData));
      dispatch(SET_RECORD_COUNT(errorRowData.length));
    }
    if (activeMaster.progress === "editOnlineConflicts")
      dispatch(UPDATE_PROGRESS_STATE("editOnlineSubmitted"));
    else dispatch(UPDATE_PROGRESS_STATE("submitted"));
    dispatch(SYNC_ACTIVE_MASTER_TO_MASTER());

    setIsConflictModalOpen(false);
  };

  function getCCRGroupKeyById(
    ccrGroupMaster: any,
    currBuff: number
  ): string | undefined {
    let val;

    // Iterate through the keys of the ccrGroupMaster object
    for (const key in ccrGroupMaster) {
      if (Object.prototype.hasOwnProperty.call(ccrGroupMaster, key)) {
        const group = ccrGroupMaster[key];

        // Check if the `ccr_group_id` matches the current buffer
        if (group?.ccr_group_id?.toString() === currBuff?.toString()) {
          val = key; // Assign the key (e.g., "CCR Stitching") to `val`
          break;
        }
      }
    }

    return val;
  }

  const getCategoryName = (id: any) => {
    if (bufferTypeData) {
      const bufferType = bufferTypeData.find((bufferType: any) => bufferType.id === id);
      return bufferType ? bufferType.nm : id;
    } else {
      return id;
    }
  };

  // function myCCRFormatter(params: any) {
  //   console.log(params, "params");
  //   console.log(params?.data[params.column.colId], "params");
  //   const currDropdownValue = params?.data[params.column.colId];

  //   let val = params?.data[params.column.colId];
  //   if (params.column.colId === "pl" || params.column.colId === "plnm") {
  //     if (plantMaster) {
  //       plantMaster.forEach((ele: any) => {
  //         if (ele?.plant_id?.toString() === currDropdownValue?.toString()) {
  //           val = ele.plant_name;
  //         }
  //       });
  //     }
  //   } else if (params.column.colId === "dp") {
  //     if (deptMaster) {
  //       deptMaster.forEach((ele: any) => {
  //         if (ele?.dept_id?.toString() === currDropdownValue?.toString()) {
  //           val = ele.dept_name;
  //         }
  //       });
  //     }
  //   } else if (params.column.colId === "cgid") {
  //     if (ccrGroupMaster) {
  //       val = getCCRGroupKeyById(ccrGroupMaster, currDropdownValue);
  //     }
  //   }
  //   return val;
  // }
  
  function myCCRFormatter(params: any, columnId?: any, isValue = false): any {
    const colId = columnId || params?.column?.colId;
    const currDropdownValue = isValue ? params : params?.data?.[colId];
    let val = currDropdownValue;
  
    if ((colId === "pl" || colId === "plnm") && plantMaster) {
      const plant = plantMaster.find(
        (ele: any) => ele?.plant_id?.toString() === currDropdownValue?.toString()
      );
      if (plant) {
        val = plant.plant_name;
      }
    } else if (colId === "dp" && deptMaster) {
      const department = deptMaster.find(
        (ele: any) => ele?.dept_id?.toString() === currDropdownValue?.toString()
      );
      if (department) {
        val = department.dept_name;
      }
    } else if (colId === "cgid" && ccrGroupMaster) {
      val = getCCRGroupKeyById(ccrGroupMaster, currDropdownValue) || currDropdownValue;
    }
  
    return val;
  }

  const getDropDown = (colField: any) => {
    if (colField === "pl" || colField === "plnm") {
      return plantMaster?.map((item: any) => item.plant_name);
    }

    if (colField === "dp") {
      return deptMaster?.map((item: any) => item.dept_name);
    }
    if (colField === "cgid") {
      return Object.keys(ccrGroupMaster);
    }
  };


  const addEditableToLastColumn = async () => {

    const modifiedColDefs = getUpdatedColDefs({
      colDefs: activeMaster.colDefs,
      activeMaster,
      bufferTypeData,
      ToggleButton,
      getDropDown,
      plantMaster,
      deptMaster,
      ccrGroupMaster,
      ccr_names,
      mode: "edit",
    });
    // const modifiedColDefs = activeMaster.colDefs.map((colDef: any) => {
    //   const editable = (params: any) => {
    //     if(activeMaster.id === 503){
    //       return params.data.ia === true
    //     }else{
    //       return params.data.iu === true
    //     }
    //   };
    //   if(colDef.field === 'actions' || colDef.field === 'iv' ){
    //     return {
    //       ...colDef,
    //       editable: false,
    //       filter:false,
    //       floatingFilter: false,
    //     }
    //   }

    //   if (colDef.field === "bt") {
    //     return {
    //       ...colDef,
    //       cellEditor: "agRichSelectCellEditor",
    //       cellEditorParams: {
    //         values: bufferTypeData?.map((item: any) => item.id),
    //         formatValue: (id: any) => getCategoryName(id)
    //       },
    //       valueGetter: (params: any) => {
    //         return getCategoryName(params?.data?.bt)
    //       },
    //       filter: 'agTextColumnFilter',
    //       cellStyle: (params: any) => {
    //         if (
    //           params.data.bid === null ||
    //           params.data.bid === undefined ||
    //           params.data.iv === false
    //         ) {
    //           return { color: "rgb(128, 0, 64)" };
    //         }
    //       },
    //       editable,
    //     };
    //   }
    //   if (
    //     colDef.field === "slt" ||
    //     colDef.field === "mlt" ||
    //     colDef.field === "bsz"
    //   ) {
    //     return {
    //       ...colDef,
    //       cellEditor: "agNumberCellEditor",
    //       cellStyle: (params: any) => {
    //         if (
    //           params.data.bid === null ||
    //           params.data.bid === undefined ||
    //           params.data.iv === false
    //         ) {
    //           return { color: "rgb(128, 0, 64)" };
    //         }
    //       },
    //       editable,
    //     };
    //   }
    //   if (colDef.field === "ib") {
    //     return {
    //       ...colDef,
    //       cellRenderer: "agCheckboxCellRenderer",
    //       cellEditor: "agCheckboxCellEditor",
    //       editable,
    //     };
    //   } else if (colDef.field === "bcd" || colDef.field === "bd") {
    //     return {
    //       ...colDef,
    //       cellStyle: (params: any) => {
    //         if (
    //           params.data.bid === null ||
    //           params.data.bid === undefined ||
    //           params.data.iv === false
    //         ) {
    //           return { color: "rgb(128, 0, 64)" };
    //         }
    //       },
    //       editable,
    //     };
    //   }

    //   if (activeMaster.id === 502) {
    //     if(colDef.field === 'actions' || colDef.field === 'iv'){
    //       return {
    //         ...colDef,
    //         editable: false,
    //         filter: false,
    //         floatingFilter: false,
            
    //       }
    //     }
        
    //     if (
    //       colDef.field === "pl" ||
    //       colDef.field === "dp" ||
    //       colDef.field === "cgid"
    //     ) {
    //       return {
    //         ...colDef,
    //         cellEditor: "agRichSelectCellEditor",
    //         valueFormatter: myCCRFormatter,
    //         cellEditorParams: {
    //           values: getDropDown(colDef.field),
    //         },
    //         editable,
    //       };
    //     }
    //     if (colDef.field === "rb") {
    //       return {
    //         ...colDef,
    //         editable,
    //         cellEditor: "agNumberCellEditor"
    //       };
    //     }
    //     if (
    //       (colDef.field === "cpd" ||
    //       colDef.field === "whpd" ||
    //       colDef.field === "sh" || 
    //       colDef.field === "fh" ||
    //       colDef.field === "cwl")
    //     ) {
    //       return {
    //         ...colDef,
    //         editable,
    //         cellEditor: "agNumberCellEditor",
    //         cellEditorParams: {
    //           min: 0,
    //           max: 1000000
    //         },
    //       };
    //     }
    //     return {
    //       ...colDef,
    //       editable,
    //     };
    //   }
    //   if (activeMaster.id === 503) {
    //     if (colDef.field === "plnm") {
    //       return {
    //         ...colDef,
    //         cellEditor: "agRichSelectCellEditor",
    //         valueFormatter: myCCRFormatter,
    //         cellEditorParams: {
    //           values: getDropDown(colDef.field),
    //         },
    //         cellStyle: (params: any) => {
    //           if (
    //             params.data.majId?.toString().startsWith("m") ||
    //             params.data.minId?.toString().startsWith("m") ||
    //             params.data.iu === true ||
    //             params.data.id === true ||
    //             params.data.ie === false
    //           ) {
    //             return { color: "rgb(128, 0, 64)" };
    //           }
    //         },
    //         editable,
    //       };
    //     }
    //     return {
    //       ...colDef,
    //       cellStyle: (params: any) => {
    //         if (
    //           params.data.majId?.toString().startsWith("m") ||
    //           params.data.minId?.toString().startsWith("m") ||
    //           params.data.ie === false ||
    //           params.data.iu === true ||
    //           params.data.id === true
    //         ) {
    //           return { color: "rgb(128, 0, 64)" };
    //         }
    //       },
    //       // editable: (params: any) =>{ (params.data.minId && params.node.rowIndex === useSelector((state: any) => state.mto.editableMinRow)) || ((!params.data.minId) && params.node.rowIndex === useSelector((state: any) => state.mto.editableMajRow))  }
    //       editable,
    //     };
    //   } else {
    //     return {
    //       ...colDef,
    //       cellEditor: "agNumberCellEditor",
    //       editable,
    //       cellStyle: (params: any) => {
    //         if (
    //           params.data.bid === null ||
    //           params.data.bid === undefined ||
    //           params.data.iv === false
    //         ) {
    //           return { color: "rgb(128, 0, 64)" };
    //         }
    //       },
    //     };
    //   }
    // });

    const isFromSaveDraft503 = prevPath === saveDraft && activeMaster.id === 503;

    if(isFromSaveDraft503){
      const newColDef = modifiedColDefs.filter((colDef: any) => colDef.field !== "actions");
      dispatch(UPDATE_COLDEFS([ ...newColDef ]));
      return
    }

    dispatch(UPDATE_COLDEFS([ actionsCol(false),...modifiedColDefs.filter((ele:any)=>ele.field!=='actions') ]));
  };

  const actionsCol = (addMinCol:boolean) => {
    return {
      field: addMinCol ? "pactions" : "actions",
      headerName: "Actions",
      colId: addMinCol ? "pactions" : "actions",
      pinned: "left",
      width: 100,
      editable: false,
      filter: false,
      floatingFilter: false,
      suppressExcelExport: true,
      cellRenderer: AddRemoveCellRenderer,
      cellRendererParams: {
        addEditableToLastColumn,
        CCRGroupMaterSetRef,
        plantMaster,
        deptMaster,
        bufferTypeData
      }
    }
  };

  const addEditableToLastMinColumn = async () => {
    const modifiedColDefs = activeMaster.colDefs.map((colDef: any) => {
      const editable = (params: any) => {
        return params.node.rowIndex === 0 && params.colDef.colId === "mindsc";
      };

      if (activeMaster.id === 503) {
        return {
          ...colDef,
          cellStyle: (params: any) => {
            if (
              params.data.majId?.toString().startsWith("m") ||
              params.data.minId?.toString().startsWith("m") ||
              params.data.ie === false ||
              params.data.iu === true ||
              params.data.id === true
            ) {
              return { color: "rgb(128, 0, 64)" };
            }
          },
          editable,
        };
      } else {
        return {
          ...colDef,
          cellEditor: "agNumberCellEditor",
          editable,
          cellStyle: (params: any) => {
            if (
              params.data.bid === null ||
              params.data.bid === undefined ||
              params.data.iv === false
            ) {
              return { color: "rgb(128, 0, 64)" };
            }
          },
        };
      }
    });

    // if (modifiedColDefs.find((colDef: any) => colDef.field === "actions")) {
    //   return;
    // }

    dispatch(UPDATE_COLDEFS([actionsCol(true), ...modifiedColDefs]));
  };

  const addRowToMtoGrid = () => {
    let newRow: any = {};


    if (activeMaster.id === 501) {
      newRow = {
        bcd: `BUFF-`,
        bd: `BUFF-`,
        bsz: "", // Example value; modify as needed
        slt: 0,
        mlt: 0,
        ib: false,
        bt: 1,
        iv: true,
        ia:true,
        iu: false,
        editable: true,
        id:uuidv4(),
        isdel: false,
      };
    } else if (activeMaster.id === 502) {
      newRow = {
        ccd: `CCR-`,
        cid: null,
        cnm: null,
        cpd: null,
        whpd: null,
        sh: null,
        fh: null,
        rb: null,
        pl: null,
        dp: null,
        a1: null,
        a2: null,
        a3: null,
        a4: null,
        a5: null,
        a6: null,
        a7: null,
        a8: null,
        a9: null,
        a10: null,
        cwl: null,
        cgid: null,
        iv: true,
        ia:true,
        iu: false,
        editable: true,
        id: uuidv4(),
        isdel: false,
      };
    } else if (activeMaster.id === 503) {
      const newId = "maj" + uuidv4();
      const newIdMin = "min" + uuidv4();
      newRow = {
        plnm: "",
        majdsc: "",
        majId: newId,
        ie: false,
        minData: [{ majId: newId, mindsc: "", minId: newIdMin, ie: false, ia: true, iu: true,}],
        ia: true,
        iu: true,
      };
      setSelectedMajReason(newRow);
    }
    // addRowToMtoMinGrid();
    dispatch(UPDATE_ROW_DATA([newRow, ...activeMaster.rowData]));
    addEditableToLastColumn();
  };

  const addRowToMtoMinGrid = () => {
    const newMinId = "min" + uuidv4();
    const newSelectedMajReason = {
      ...selectedMajReason,
      minData: [
        {
          majId: selectedMajReason.majId,
          ie: false,
          minId: newMinId,
          mindsc: "",
       
        },
        ...selectedMajReason.minData,
      ],
    };
    const newRowData: any = [];
    activeMaster.rowData.forEach((element) => {
      if (element.majId === selectedMajReason.majId) {
        newRowData.push(newSelectedMajReason);
      } else {
        newRowData.push(element);
      }
    });
    dispatch(UPDATE_ROW_DATA(newRowData));
    setSelectedMajReason(newSelectedMajReason);
    addEditableToLastMinColumn();
  };


  const AddCalendarModifyData = (data: any) => {
    data?.forEach((el:any)=>{
      if(!Array.isArray(el.ccr_id) && !el.hid && !el.plid){
        const ccrIdAndPlantIdFromName = ccrsData.find((ccr: any) => ccr.cnm.toLowerCase().trim() === el.ccr_id.toLowerCase().trim());
        if(ccrIdAndPlantIdFromName){
          el.ccr_id = [ccrIdAndPlantIdFromName.cid];
          el.plid = ccrIdAndPlantIdFromName.plant;
          el.hid = null;
          el.rd = null;
          el.rb = '';
          el.sd = moment(el.sd).format('YYYY-MM-DD');
          el.ed = moment(el.ed).format('YYYY-MM-DD');
          el.dow = []
          el.iu = false
          el.id = false
        }else{
          throw new Error("CCR || Plant name is not valid");
        }
      
      }
    })
    return data
  }

  const saveCalendarTask = async(pageType: string) => {
    const calendarObj:any = {
      mid : activeMaster.id,
      uid : user.user.user.id.toString(),
      unm : user.user.user.name,
      at : pageType === "add" ? "Add" : "Modify",
      cData: []
    }

    try {

    if(pageType === "modify"){
      
      const newData = _.cloneDeep(activeMaster.rowData)
      newData.forEach((el :any)=>{
        if((el.ia && !el.id )|| el.iu || (el.id && !el.ia) || el.iu === false || el.id === false){
          if(el.ia){
            el.hid = null
          }
          calendarObj.cData.push(el)
        } 
      })
    }else if(pageType === "add"){
      const newDataAdd = _.cloneDeep(activeMaster.rowData)
      calendarObj.cData = AddCalendarModifyData(newDataAdd)
    } 

    if(calendarObj.cData.length === 0){
      notifyError("No Data to Save!");
      return;
    }

    
      notifyLoader("Saving Task...");
      
      const response = await saveCalendarMasterTask(calendarObj)

      if( response.status !== 200){
        notifyError("Failed to create task!");
        return;
      }

      if(pageType === "add"){
        dispatch(UPDATE_ROW_DATA([]));

        navigate(-1);
        resetMtoMasters();
        RESET_MTO_STATE();
      }else if(pageType === 'modify' ){
        dispatch(UPDATE_ROW_DATA(calendarInitialData));
        setMTOProgress("submitted Once");
      }
      notifySuccess(response.data.msg || "Saved Calendar Task Successfully");
    } catch (error:any) {
      console.error(error.msg || error)
      notifyError(error ? "CCR | Plant name is not valid" : "Failed to create Draft!");
    }
  }

  const saveCalendarDraft = async (pageType: string) => {
    const calendarObj: any = {
      mid: activeMaster.id,
      uid: user.user.user.id.toString(),
      unm: user.user.user.name,
      at: pageType === "add" ? "Add" : "Modify",
      cData: [],
    };
    try {
      if (pageType === "modify") {
        const newDataModify = _.cloneDeep(activeMaster.rowData);

        newDataModify.forEach((el: any) => {
          if (el.ia || el.iu || el.id || !el.hid) {
            if (el.ia) {
              el.hid = null;
            }
            calendarObj.cData.push(el);
          }
        });

        if (calendarObj.cData.length === 0) {
          notifyError("No Data to Save!");
          return;
        }
      } else if (pageType === "add") {
        const newDataAdd = _.cloneDeep(activeMaster.rowData);
        calendarObj.cData = AddCalendarModifyData(newDataAdd);
      }

      notifyLoader("Saving Draft...");

      const response = await saveCalendarMasterDraft(calendarObj);

      if (response?.status !== 200) {
        notifyError("Failed to create Draft!");
        return;
      }
      notifySuccess(response?.data?.msg || "Draft Created Successfully");
    } catch (error: any) {
      console.error(error.msg || error);
      notifyError(
        error ? "CCR | Plant name is not valid" : "Failed to create Draft!"
      );
    }
  };


  const onMTOAddSaveBufferData = async () => {
    notifyLoader("Saving Task...");
    const BufferPostObj: any = {
      mid: activeMaster.id,
      uid: user.user.user.id.toString(),
      unm: user.user.user.name,
      buffData: [],
      at: pageType === "add" ? "Add" : "Modify",
    };

    let isValid = true;

    const selectedRows: any = _.cloneDeep(activeMaster.rowData);
    selectedRows.forEach((e: any) => {
      const newVal = JSON.parse(JSON.stringify(e));
      bufferTypeData.forEach((ele: any) => {
        if (ele.nm === e.bt) {
          newVal.bt = ele.id;
        }
      });

      newVal.ib = (e.ib === "false"|| e.ib===false) ? false : true;
      newVal.iv = e.iv === true || e.iv === false ? e.iv : true;
      newVal.mlt = parseInt(e.mlt);
      newVal.slt = parseInt(e.slt);
      newVal.bid = null;

      if (newVal.err.error.length > 0 || newVal.err.warning.length > 0) {
        isValid = false;
      }

      BufferPostObj.buffData.push(_.omit(newVal, ["editable", "err"]));
    });

    if (!isValid) {
      toast.dismiss();
      notifyError("You cannot save a task with error!");
      return;
    }

    try {
      const response = await saveBufferMasterTask(BufferPostObj);
      if (response.status == 200) {
        toast.dismiss();
        const allData = [...activeMaster.rowData];
        const indexesToRemove = selectedRows.map((row: any) =>
          allData.indexOf(row)
        );
        indexesToRemove.sort((a: any, b: any) => b - a);
        // indexesToRemove.forEach((index:number) => allData.splice(index,1));
        const newData: any = [];
        allData.forEach((e: any, index: any) => {
          if (!indexesToRemove.includes(index)) newData.push(e);
        });

        dispatch(UPDATE_ROW_DATA(newData));

        navigate(-1);
        resetMtoMasters();
        RESET_MTO_STATE();
        notifySuccess("Buffer task updated!!");
      } else {
        toast.dismiss();
        notifyError(
          "Failed to create the task....Please check your validations!"
        );
      }
    } catch (error) {
      toast.dismiss();
      notifyError("Failed to create task!");
      console.error(error);
    }
  };

  const onMTOAddCCRData = async () => {
    notifyLoader("Saving Task...");

    const CCRPostObj: any = {
      mid: activeMaster.id,
      uid: user.user.user.id.toString(),
      unm: user.user.user.name,
      ccrData: [],
      at: pageType === "add" ? "Add" : "Modify",
    };
    const selectedRows: any = _.cloneDeep(activeMaster.rowData);
    let isValid = true;
    selectedRows.forEach((e: any) => {
      const newVal = _.cloneDeep(e);
      newVal.cid = e.cid ? e.cid : null;
      const ccrGid = ccrGroupMaster[e.cgid]?.ccr_group_id
      ? ccrGroupMaster[e.cgid]?.ccr_group_id
      : e.cgid;
      newVal.cgid = isNaN(ccrGid)?e.ccr_group: ccrGid;
      newVal.plid = e.pl;
      newVal.dpid = e.dp;
      newVal.iv = (e.iv===true||e.iv==false)?e.iv: true;
      deptMaster.forEach((elm: any) => {
        if (elm.dept_name === e.dp) newVal.dpid = elm.dept_id;
      });
      plantMaster.forEach((elm: any) => {
        if (elm.plant_name === e.pl) newVal.plid = elm.plant_id;
      });
      if (newVal.err.error !== "") {
        isValid = false;
      }
      CCRPostObj.ccrData.push(_.omit(newVal, ["editable", "err"]));
    });
    if (!isValid) {
      toast.dismiss();
      notifyError(
        "Make sure you have resolved the error for the selected row!"
      );
      return;
    }

    try {
      const response = await saveCCRMasterTask(CCRPostObj);
      if (response.status == 200) {
        toast.dismiss();
        const allData = [...activeMaster.rowData];
        const indexesToRemove = selectedRows.map((row: any) =>
          allData.indexOf(row)
        );
        indexesToRemove.sort((a: any, b: any) => b - a);
        // indexesToRemove.forEach((index:number) => allData.splice(index,1));
        const newData: any = [];
        allData.forEach((e: any, index: any) => {
          if (!indexesToRemove.includes(index)) newData.push(e);
        });

        dispatch(UPDATE_ROW_DATA(newData));

        navigate(-1);
        resetMtoMasters();
        RESET_MTO_STATE();
        notifySuccess("CCR task updated!!");
      } else {
        toast.dismiss();
        notifyError(
          "Failed to create the task....Please check your validations!"
        );
      }
    } catch (error) {
      console.error(error);
      toast.dismiss();
      notifyError("Failed to create task!");
    }
  };
  const onMTOAddPoogiData = async () => {
    notifyLoader("Saving Poogi Task...");

    const PoogiPostObj: any = {
      mid: activeMaster.id,
      uid: user.user.user.id.toString(),
      unm: user.user.user.name,
      at: pageType === "add" ? "Add" : "Modify",
      reasonData: [],
    };
    const selectedRows: any = _.cloneDeep(activeMaster.rowData);
    let isValid = true;

    selectedRows.forEach((e: any) => {
      const newVal = _.cloneDeep(e);
      newVal.plid = e.plnm;
      plantMaster.forEach((elm: any) => {
        if (elm.plant_name === e.plnm) newVal.plid = elm.plant_id;
      });
      if (newVal.err.error !== "") {
        isValid = false;
      }
      PoogiPostObj.reasonData.push(_.omit(newVal, ["editable", "err"]));
    });
    if (!isValid) {
      toast.dismiss();
      notifyError(
        "Make sure you have resolved the error for the selected row!"
      );
      return;
    }

    const finPoogiPostData: any = [];
    const groupedData = _.groupBy(PoogiPostObj.reasonData, "majdsc");

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    for (const [key,items] of Object.entries(groupedData)) {
      items.forEach((item) => {
        const { plnm, plid, majdsc, mindsc } = item;
        let existingMajor = finPoogiPostData.find(
          (major: any) => major.plnm === plnm && major.majdsc === majdsc
        );

        if (!existingMajor) {
          existingMajor = {
            majdsc,
            majid: null,
            majId: null,
            majcd: "*",
            minData: [],
            iu: false,
            ie: false,
            id: false,
            plnm,
            pl: plid,
            plid,
          };
          finPoogiPostData.push(existingMajor);
        }

        existingMajor.minData.push({
          mindsc,
          minid: null,
          majid: null,
          majId: null,
          minId: null,
          mincd: "*",
          iu: false,
          ie: false,
          id: false,
        });
      });
    }
    PoogiPostObj.reasonData = finPoogiPostData;
    try {
      const response = await savePOOGIMasterTask(PoogiPostObj);

      if (response.status === 200) {
        dispatch(UPDATE_ROW_DATA([]));
        dispatch(SET_POOGI_MODIFY_DATA([]));
        toast.dismiss();
        navigate(-1);
        resetMtoMasters();
        RESET_MTO_STATE();
        notifySuccess("Poogi task updated!!");
      } else {
        toast.dismiss();
        notifyError(
          "Failed to create the task....Please check your validations!"
        );
      }
    } catch (error) {
      toast.dismiss();
      notifyError("Failed to save task");
      console.error(error);
    }
  };

  const keysToDelete = (ele:any)=>{
      const e = _.cloneDeep(ele);
      delete e.isdel;
      delete e.id;
      
      return e
  }

  const onMTOSaveBufferData = async () => {
    
    if(location?.state?.draftId){
      try{
        await deleteDraft(location?.state?.draftId)
      }
      catch(e){
        toast.dismiss();
        notifyError("Failed to save Draft!")
        return;
      }
    }

    // on MDM add records
    if (pageType === "add") {
      if (activeMaster.id === 501) {
        onMTOAddSaveBufferData();
      } else if (activeMaster.id === 502) {
        onMTOAddCCRData();
      } else if (activeMaster.id === 503) {
        onMTOAddPoogiData();
      }else if(activeMaster.id === 504){
        saveCalendarTask(pageType);
      }
      return;
    }

    const incompleteData = activeMaster.rowData.find((rowdata: any) =>
      rowdata.editable == true
    );
    if (incompleteData) {
      setShowModal(true);
    } else {
      onIncompleteDataConfirm();
    }
  };

  const onIncompleteDataConfirm = async () => {
    if (activeMaster.id === 501) {
      notifyLoader("Saving Task...");
      const BufferPostObj: any = {
        mid: activeMaster.id,
        uid: user.user.user.id.toString(),
        unm: user.user.user.name,
        at: pageType === "add" ? "Add" : "Modify",
        buffData: [],
      };

      const bufferData = bufferModifyData?.filter((ele: any) => !ele.isdel)
      bufferData.forEach((ele: any) => {
        const e = keysToDelete(ele);
        bufferTypeData.forEach((elm: any) => {
          if (elm.nm === ele.bt) {
            e.bt = elm.id;
          }
        });
        e.ib = (e.ib === "false" || e.ib === false) ? false : true;
        e.mlt = parseInt(e.mlt);
        e.slt = parseInt(e.slt);
        e.iv = (e?.iv === false || e?.iv === true) ? e.iv : true
        if (!e.bid) e.bid = null;

     
        BufferPostObj.buffData.push(
          _.omit(e, ["editable", "error", "warning"])
        );
      
      });

      try {
        const response = await saveBufferMasterTask(BufferPostObj);
        if (response.status === 200) {
          notifySuccess("Saved Buffer Task Successfully");
          dispatch(UPDATE_ROW_DATA(bufferInitialData));
          dispatch(SET_BUFFER_MODIFY_DATA([]));
          setMTOProgress("submitted Once");
        } else {
          toast.dismiss();
          notifyError(
            "Failed to create the task....Please check your validations!"
          );
        }
      } catch (error) {
        toast.dismiss();
        notifyError("Failed to create task!");
        console.error(error);
      }
    } else if (activeMaster.id === 502) {

      notifyLoader("Saving CCR Task...");
      const CCRPostObj: any = {
        mid: activeMaster.id,
        uid: user.user.user.id.toString(),
        unm: user.user.user.name,
        at: pageType === "add" ? "Add" : "Modify",
        ccrData: [],
      };

      const ccrData = ccrModifyData?.filter((ele:any)=> !ele.isdel)

      ccrData.forEach((ele: any) => {
        const e = keysToDelete(ele)
        const ccrGid = ccrGroupMaster[e.cgid]?.ccr_group_id
          ? ccrGroupMaster[e.cgid]?.ccr_group_id
          : e.cgid;
        e.cgid = ccrGid || e.ccr_group;
        e.plid = e.pl;
        e.dpid = e.dp;
        deptMaster.forEach((elm: any) => {
          if (elm.dept_name === ele.dp) e.dpid = elm.dept_id;
        });
        plantMaster.forEach((elm: any) => {
          if (elm.plant_name === ele.pl) e.plid = elm.plant_id;
        });
        CCRPostObj.ccrData.push(
          _.omit(e, ["editable", "error", "warning", "pl", "dp"])
        );
      });


      try {
        const response = await saveCCRMasterTask(CCRPostObj);
        if (response.status === 200) {
          toast.dismiss();
          notifySuccess("Saved CCR Task Successfully");
          dispatch(UPDATE_ROW_DATA(ccrInitialData));
          dispatch(SET_CCR_MODIFY_DATA([]));
          setMTOProgress("submitted Once");
        } else {
          toast.dismiss();
          notifyError("Failed to create the task...");
        }
      } catch (error) {
        toast.dismiss();
        notifyError("Failed to create task!");
        console.error(error);
      }

      return;
    } else if (activeMaster.id === 503) {
      notifyLoader("Saving POOGI Task...");
      const POOGIPostObj: any = {
        mid: activeMaster.id,
        uid: user.user.user.id.toString(),
        unm: user.user.user.name,
        reasonData: [],
        at: pageType === "add" ? "Add" : "Modify",
      };

      poogiModifyData?.forEach((ele: any) => {
        const e = _.cloneDeep(ele);
        e.majid = ele.majId;
        e.majcd = ele.majcd ? ele.majcd : "*";
        if (typeof e.majId === "string" && e.majId.startsWith("m")) {
          e.majId = null;
          e.majid = null;
          e.ie = false;
        } else {
          e.ie = true;
        }
        e.id = ele.id ? ele.id : false;
        e.iu = ele.iu ? ele.iu : false;

        // Iterate through minData to check and update minId if it starts with 'm'
        e.minData.forEach((minElement: any) => {
          minElement.id = minElement.id ? minElement.id : false;
          if (
            typeof minElement.minId === "string" &&
            minElement.minId.startsWith("m")
          ) {
            minElement.minId = null;
            minElement.majId = null;
            minElement.minid = null;
            minElement.majid = null;
            minElement.ie = false;
            minElement.mincd = minElement.mincd ? minElement.mincd : "*";
          } else {
            minElement.ie = true;
          }
          minElement.minid = minElement.minId;
          minElement.majid = minElement.majId;
          minElement.mincd = minElement.mincd ? minElement.mincd : "*";
          minElement.iu = minElement.iu ? minElement.iu : false;
        });

        plantMaster?.forEach((elm: any) => {
          if (elm.plant_name === ele.plnm) e.pl = elm.plant_id;
        });
        POOGIPostObj.reasonData.push(
          _.omit(e, ["editable", "error", "warning", "plnm"])
        );
      });
      try {
        const response = await savePOOGIMasterTask(POOGIPostObj);
        if (response.status === 200) {
          toast.dismiss();
          notifySuccess("Saved POOGI Task Successfully");
          const newPoogiInitialData = _.cloneDeep(poogiInitialData);
          const finNewPoogiInitialData = newPoogiInitialData.filter(
            (item: any) =>
              !item.majId?.toString().startsWith("m") &&
              !item.minData.some((minItem: any) =>
                minItem.minId?.toString().startsWith("m")
              )
          );
          dispatch(UPDATE_ROW_DATA(finNewPoogiInitialData));
          dispatch(SET_POOGI_INITIAL_DATA(newPoogiInitialData));
          dispatch(SET_POOGI_MODIFY_DATA([]));
          setMTOProgress("submitted Once");
        } else {
          toast.dismiss();
          notifyError("Failed to create the task...");
        }
      } catch (error) {
        toast.dismiss();
        notifyError("Failed to create task!");
        console.error(error);
      }
      return;
    } else if( activeMaster.id === 504){
      saveCalendarTask(pageType);
      return;
    }

  }


  const onMTOSaveAsDraft = async () => {
    notifyLoader("Saving Draft...");

    if(location?.state?.draftId){
      try{
        await deleteDraft(location?.state?.draftId)
      }
      catch(e){
        toast.dismiss();
        notifyError("Failed to save Draft!")
        return;
      }
    }

    if (activeMaster.id === 501) {
      const BufferPostObj: any = {
        mid: activeMaster.id,
        uid: user.user.user.id.toString(),
        unm: user.user.user.name,
        buffData: [],
        at: pageType === "add" ? "Add" : "Modify",
      };

      if (pageType === "add") {
        activeMaster.rowData.forEach((ele: any) => {
          const e = _.cloneDeep(ele);
          bufferTypeData?.forEach((elm: any) => {
            if (elm.nm === ele.bt || elm.id === ele.bt ) {
              e.bt = elm.id;
            }
          });
          e.ib = (e.ib === "false"|| e.ib===false) ? false : true;
          e.mlt = parseInt(e.mlt);
          e.slt = parseInt(e.slt);
          e.err = "";
          e.iv = true;
          if (!e.bid) e.bid = null;

          if (e.bid === null || e.iv === false) {
            BufferPostObj.buffData.push(
              _.omit(e, ["editable", "error", "warning"])
            );
          }
        });
      } else {
        const bufferData = bufferModifyData?.filter((ele:any)=> !ele.isdel)

        bufferData.forEach((ele: any) => {
          const e = keysToDelete(ele)
          bufferTypeData?.forEach((elm: any) => {
            if (elm.nm === ele.bt || elm.id === ele.bt ) {
              e.bt = elm.id;
            }
          });
          e.ib = (e.ib === "false"|| e.ib===false) ? false : true;
          e.mlt = parseInt(e.mlt);
          e.slt = parseInt(e.slt);
          e.err = "";
          !(e.iv === true || e.iv === false) && (e.iv = false);
          if (!e.bid) e.bid = null;

          
          BufferPostObj.buffData.push(
            _.omit(e, ["editable", "error", "warning"])
          );
          
        });
      }
      try {
        const response = await saveBufferMasterDraft([BufferPostObj]);
        if (response.status === 200) {
          toast.dismiss();
          notifySuccess("Saved Draft Successfully");
        } else {
          toast.dismiss();
          notifyError("Failed to save draft!");
        }
      } catch (error) {
        console.error(error);
        toast.dismiss();
        notifyError("Failed to save draft!");
      }
    } else if (activeMaster.id === 502) {
      notifyLoader("Saving CCR Draft...");
      const CCRPostObj: any = {
        mid: activeMaster.id,
        uid: user.user.user.id.toString(),
        unm: user.user.user.name,
        ccrData: [],
        at: pageType === "add" ? "Add" : "Modify",
      };
      let tempModifyData = ccrModifyData?.filter((ele:any)=> !ele.isdel);
      if (pageType === "add") {
        tempModifyData = _.cloneDeep(activeMaster.rowData);
      }
      tempModifyData.forEach((ele: any) => {
        let e = keysToDelete(ele)
        if(pageType === 'add'){
          e = _.cloneDeep(ele);
        }
        e = _.cloneDeep(ele);
        const ccrGid = ccrGroupMaster[e.cgid]?.ccr_group_id
          ? ccrGroupMaster[e.cgid]?.ccr_group_id
          : e.cgid;
        e.cid = ele.cid ? ele.cid : null;
        e.cgid = isNaN(ccrGid)?e.ccr_group: ccrGid;
        e.plid = e.pl;
        e.dpid = e.dp;
        deptMaster.forEach((elm: any) => {
          if (elm.dept_name === ele.dp) e.dpid = elm.dept_id;
        });
        plantMaster.forEach((elm: any) => {
          if (elm.plant_name === ele.pl) e.plid = elm.plant_id;
        });
        e.cpd = parseInt(e.cpd);
        e.whpd = parseInt(e.whpd);
        e.fh = parseInt(e.fh);
        e.rb = Number(e.rb);
        e.cwl = parseInt(e.cwl);
        e.sh = parseInt(e.sh);
        e.iv = (e.iv===true||e.iv==false)?e.iv: true;
        e.err = "";
        CCRPostObj.ccrData.push(_.omit(e, ["editable", "error", "warning"]));
      });

      try {
        const response = await saveCCRMasterDraft([CCRPostObj]);
        if (response.status === 200) {
          toast.dismiss();
          notifySuccess("Saved CCR Draft Successfully");
        } else {
          toast.dismiss();
          notifyError("Failed to save draft...");
        }
      } catch (error) {
        console.error(error);
        toast.dismiss();
        notifyError("Failed to save draft!");
      }

      return;
    } else if (activeMaster.id === 503) {
      notifyLoader("Saving POOGI Draft...");

      if(pageType==='add'){
        notifyLoader("Saving Poogi Draft...");
    
        const PoogiPostObj: any = {
          mid: activeMaster.id,
          uid: user.user.user.id.toString(),
          unm: user.user.user.name,
          at: pageType === "add" ? "Add" : "Modify",
          reasonData: [],
        };
        const selectedRows: any = _.cloneDeep(activeMaster.rowData);
        let isValid = true;
    
        selectedRows.forEach((e: any) => {
          const newVal = _.cloneDeep(e);
          newVal.plid = e.plnm;
          plantMaster.forEach((elm: any) => {
            if (elm.plant_name === e.plnm) newVal.plid = elm.plant_id;
          });
          if (newVal.err.error !== "") {
            isValid = false;
          }
          PoogiPostObj.reasonData.push(_.omit(newVal, ["editable", "err"]));
        });
        if (!isValid) {
          toast.dismiss();
          notifyError(
            "Make sure you have resolved the error for the selected row!"
          );
          return;
        }
    
        const finPoogiPostData: any = [];
        const groupedData = _.groupBy(PoogiPostObj.reasonData, "majdsc");
    
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        for (const [key,items] of Object.entries(groupedData)) {
          items.forEach((item) => {
            const { plnm, plid, majdsc, mindsc } = item;
            let existingMajor = finPoogiPostData.find(
              (major: any) => major.plnm === plnm && major.majdsc === majdsc
            );
    
            if (!existingMajor) {
              existingMajor = {
                majdsc,
                majid: null,
                majId: null,
                majcd: "*",
                minData: [],
                iu: false,
                ie: false,
                id: false,
                plnm,
                pl: plid,
                plid,
                err:""
              };
              finPoogiPostData.push(existingMajor);
            }
    
            existingMajor.minData.push({
              mindsc,
              minid: null,
              majId: null,
              minId: null,
              mincd: "*",
              iu: false,
              ie: false,
              id: false,
              err: ""
            });
          });
        }
        PoogiPostObj.reasonData = finPoogiPostData;
        
        try {
          const response = await savePOOGIMasterDraft([PoogiPostObj]);
    
          if (response.status === 200) {
            toast.dismiss();
            notifySuccess("Poogi Draft updated!!");
          } else {
            toast.dismiss();
            notifyError(
              "Failed to create the draft....Please check your validations!"
            );
          }
        } catch (error) {
          toast.dismiss();
          notifyError("Failed to save draft");
          console.error(error);
        }
        return;
      }

      const POOGIPostObj: any = {
        mid: activeMaster.id,
        uid: user.user.user.id.toString(),
        unm: user.user.user.name,
        reasonData: [],
        at: pageType === "add" ? "Add" : "Modify",
      };


      poogiModifyData?.forEach((ele: any) => {
        const e = _.cloneDeep(ele);
        if (typeof e.majId === "string" && e.majId.startsWith("m")) {
          e.majId = null;
          e.majid = null;
          e.ie = false;
        } else {
          e.ie = true;
          e.majid = e.majId;
        }
        e.id = ele.id ? ele.id : false;
        e.iu = ele.iu ? ele.iu : false;
        e.majcd = ele.majcd ? ele.majcd : "*";
        e.err = "";

        // Iterate through minData to check and update minId if it starts with 'm'
        e.minData.forEach((minElement: any) => {
          minElement.id = minElement.id ? minElement.id : false;
          if (
            typeof minElement.minId === "string" &&
            minElement.minId.startsWith("m")
          ) {
            minElement.minId = null;
            minElement.ie = false;
            if(minElement?.majId && minElement?.majId?.length && minElement?.majId?.startsWith("m")){
              minElement.majId = null;
              minElement.majid = null;
            }
            minElement.mincd = minElement.mincd ? minElement.mincd : "*";
          } else {
            minElement.ie = true;
          }
          minElement.minid = minElement.minId;
          minElement.majid = minElement.majId;
          minElement.mincd = minElement.mincd ? minElement.mincd : "*";
          minElement.iu = minElement.iu ? minElement.iu : false;
          minElement.err = "";
        });

        plantMaster?.forEach((elm: any) => {
          if (elm.plant_name === ele.plnm) e.pl = elm.plant_id;
        });
        POOGIPostObj.reasonData.push(
          _.omit(e, ["editable", "error", "warning", "plnm"])
        );
      });
      try {
        const response = await savePOOGIMasterDraft([POOGIPostObj]);
        if (response.status === 200) {
          toast.dismiss();
          notifySuccess("Saved POOGI Draft Successfully");
        } else {
          toast.dismiss();
          notifyError("Failed to save as draft...");
        }
      } catch (error) {
        toast.dismiss();
        notifyError("Failed to save as draft!");
        console.error(error);
      }

      return;
    }else if(activeMaster.id === 504){
      saveCalendarDraft(pageType);
      return;
    }
  };

  useEffect(() => {
    if (pageType === "add") {
      if (bufferInitialData || ccrInitialData) {
        if ((ccrGroupMaster && plantMaster && deptMaster) || bufferTypeData) {
          const newRowData = _.cloneDeep(activeMaster.rowData);
          newRowData.forEach((ele: any) => {
            if (typeof ele.err === "string"  ) {
              ele.err = { error: "" };
            } else if(ele.err && ele.err.error){
              ele.err.error = "";
            }
          });
          validateMTOMaster(activeMaster.id, newRowData);
          return;
        }
      }
    }
  }, [
    bufferInitialData,
    ccrInitialData,
    bufferTypeData,
    ccrGroupMaster,
    plantMaster,
    deptMaster
  ]);

  const onMajReasonSelected = () => {
    setSelectedMajReason(ref?.current?.api?.getSelectedRows()[0]);
  };

  const onMinReasonEditingStopped = (params: any) => {
    const newData = _.cloneDeep(activeMaster.rowData);
    let majIdIndex = 0;
    activeMaster.rowData.forEach((ele: any, index: number) => {
      if (ele?.majId === selectedMajReason?.majId) {
        majIdIndex = index;
      }
    });

    newData[majIdIndex] &&
      (newData[majIdIndex].minData[params.node.rowIndex].mindsc =
        params.newValue);
    dispatch(UPDATE_ROW_DATA(newData));
    setSelectedMajReason(newData[majIdIndex]);
  };

  const getCombinedPoogiDataForExcelExport = () => {
    if(activeMaster?.id!== 503) return [];
    const allRowsData:any = []
    
    activeMaster?.rowData?.forEach((ele => {
    
        ele?.minData?.forEach((minEle: any) => {
          allRowsData.push(
            {majdsc: ele.majdsc, mindsc: minEle.mindsc, plnm: ele.plnm}
          )
        });
      
    }
    ))
    return allRowsData;

  }

  return {
    colDefs,
    isSelectMasterOpen,
    options,
    selectedOptions,
    activeMaster,
    filterButtonStatus,
    setFilterButtonStatus,
    handleSelectMasterSubmit,
    handleTabChange,
    handleTabClose,
    addNewMaster,
    handleOnAddFilter,
    handleOnDeleteFilter,
    allMastersState,
    handleApplyFilter,
    isWarningModalOpen,
    toggleWarningModal,
    onWarningModalClose,
    onWarningModalSuccess,
    isUploadModalOpen,
    toggleUploadModal,
    calendarFormData,
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
    handleChangePage,
    isLoading,
    onReset,
    onEditOnlineSave,
    chartData,
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
    validResumeStatuses,
    validStopStatuses,
    onPIPOStatusUpdate,
    enableEditOnlineReset,
    uploadProgress,
    plantNames,
    ccrNames,
    isModalOpen,
    setIsModalOpen,
    totalProgress,
    tempRecordCount,
    addRowToMtoGrid,
    onMTOSaveBufferData,
    // selectedDays,
    // setSelectedDays,
    // toggleDay,
    onSaveHandler,
    onDeleteHandler,
    selectedData,
    setSelectedData,
    onMTOSaveAsDraft,
    setCalendarFormData,
    onExcelExport,
    MTOPoogiMinorColdef: [
      {
        headerName: "Sr No.",
        maxWidth: 90,
        cellStyle: {
          textAlign: "center",
        },
        valueGetter: "node.rowIndex + 1",
      },
      ...activeMaster.colDefs
        .filter(
          (ele: any) =>
            ele.field === "pactions" ||
            ele.colId === "minId" ||
            ele.colId === "mindsc"
        )
        .map((col: any) => {
          if (col.colId === "mindsc") {
            return {
              ...col,
              cellRenderer: MinReasonDescCell,
            };
          }
          return col;
        }),
      {
        headerName: "Action",
        cellRenderer: "poogiEditDeleteCellRenderer",
        maxWidth: 100,
        filter: false
      },
    ],
    MTOPoogiMajorColdef: [
      {
        headerName: "Sr No.",
        maxWidth: 90,
        cellStyle: {
          textAlign: "center",
        },
        valueGetter: "node.rowIndex + 1",
      },
      ...activeMaster.colDefs
        .filter(
          (ele: any) =>
            ele.field === "actions" ||
            ele.colId === "majId" ||
            ele.colId === "majdsc" ||
            ele.colId === "plnm"
        )
        .map((col: any) => {
          if (col.colId === "majdsc") {
            return {
              ...col,
              cellRenderer: MajReasonDescCell,
            };
          }
          else if(col.colId === 'plnm'){
            return {
              ...col,
              cellEditor: "agRichSelectCellEditor",
              cellEditorParams: {
                values: plantMaster?.map((item: any) => item.plant_name),
              },
            }
          }
          return col;
        }),
      {
        headerName: "Action",
        cellRenderer: "poogiEditDeleteCellRenderer",
        maxWidth: 100,
        filter: false
      },
    ],

    onMajReasonSelected,
    // minReasonRowData: selectedMajReason? (activeMaster.rowData.filter((ele: any) => ele.majId === selectedMajReason?.majId)[0]?.minData):(useSelector((state: any) => state.mto.editableMinRow))? activeMaster.rowData[useSelector((state: any) => state.mto.editableMinRow)]?.minData: [],
    minReasonRowData: selectedMajReason ? selectedMajReason.minData : [],
    onMinReasonEditingStopped,
    addRowToMtoMinGrid,
    mtoProgress,
    getCombinedPoogiDataForExcelExport,
    showModal,
    setShowModal,
    bufferDataConfirm: onIncompleteDataConfirm,
    isAPILoading
  };
};
export default useViewModify;
