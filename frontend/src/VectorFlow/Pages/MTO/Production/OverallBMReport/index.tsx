import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import MTOActionToolBar from "../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar";
import {
  BMDepWrapper,
  BMDepHeaderWraper,
  VFWrapper,
} from "../DepartmentWiseBMReport/styles";
import {
  BTRAllomentSection,
  BTRTableWrapper,
  HorizontalViewWrapper,
} from "../../Common/SplitGraphContainer/styles";
import { Allotment } from "allotment";
//import BPRRemarkHistoryModal from '../DepartmentWiseBMReport/MTORemarkHistoryModal';
// import useViewPort from '../../../../../hooks/useViewPort';
import { AgGridReactProps } from "ag-grid-react";
import BPPRenderer from "../../Common/BPRRenderer/BPPRenderer";
import AgeingCellRenderer from "../DepartmentWiseBMReport/AgeingIconCellRenderer";
//import customCellRenderer from '../DepartmentWiseBMReport/CustomCellRenderer';
import RemarkHistoryRenderer from "../DepartmentWiseBMReport/RemarkHistoryRenderer";
import GridView from "../DepartmentWiseBMReport/GridView";
import OrderElapsedGrid from "../DepartmentWiseBMReport/OrderElapsedGrid";
import {
  useGetOverAllBMReport,
  useShortOrderCompleteOrder,
} from "../../../../Services/MTO/Production/OverallBMReport/index";
import {
  notifyError,
  notifyLoader,
  notifySuccess,
} from "../../../../../helpers/notify";
import { useGetBOMExplosionData } from "../../../../../VectorFlow/Services/MTO/Common/BOMExplosion";
import { useGetPoogiRemarks } from "../../../../../VectorFlow/Services/MTO/Poogi/ReasonOrderChange/index";
import BPRRemarkHistoryModal from "../DepartmentWiseBMReport/MTORemarkHistoryModal";
import {
  useGetDeptWiseWipData,
  useGetHighAgeingData,
} from "../../../../../VectorFlow/Services/MTO/Production/DepartmentWiseBMReport/index";
import { IRowNode } from "ag-grid-enterprise";
import OverlayLoader from "../../Common/Loader";
import { ColorsMTO } from "../../Common/Colors";
import { useGetFilterData } from "../../../../../VectorFlow/Services/MTO/Common/CommonFilter";
import useFilter from "../../../../../hooks/useFilter";
import { formatFilterJSON, getColumnDefinations,DownloadExcel, getBodyForExcelExport } from "../../../../../helpers/utils";
import { useGetUIConfigData } from "../../../../../VectorFlow/Services/MTO/Common/UIConfig";
import { ExcelExportName, FilterPageName, UIGridCode } from "../../Common/Enum";
import { useDispatch } from "react-redux";
import { BM_REPORT_ANALYTICS } from "../../../../../redux/actions/MTO";
import { modifyAnalyticsData } from "../DepartmentWiseBMReport/helper";
import { useGetDBRsettingsData } from '../../../../Services/MTO/Common/DBRSettings';
import _ from "lodash";
import {
  useGetUserUIConfigData,
  useUpdateUserUIConfigData,
} from "../../../../../VectorFlow/Services/MTO/Common/UserUIConfig";
import { useUserData } from "../../../../../context";
import { useGetDate } from "../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/RMPMExpediting";
import moment from "moment";
import VFSelect from "../../../../../../src/components/VectorFLOW/commons/MTO/VFSelect";
import ConfirmationModal from "./ConfirmationModal";
import { InputCheckBox } from "./styles";
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton";
import BomExcelModal from "../../Common/BomExcelModal";
import useColDef from "../../../../../hooks/useColDef";
import { createDynamicColumnDefs } from "../../../../../helpers/gridUtils";
import CustomHeaderCheckbox from "../../../../../VectorFlow/Pages/MTO/Common/CustomHeaderCheckbox";


interface ApiResponse {
  cc: string;
  cp: number;
  hd: string;
  v: boolean;
  cla: string;
  scc: string;
  children?: ApiResponse[];
  cgs?: string;
  pinned?: string;
  dt?: string;
}

interface ColDefChild {
  field: string;
  headerName: string;
  colId: string;
  cellRenderer?: string;
  initialWidth?: number;
  floatingFilter?: boolean;
  columnGroupShow?: string;
  pinned?: any;
  cellRendererParams?: {
    onClick?: (data: string) => Promise<void>;
  };
}

type orderkeyObj = {
  ok: [];
};

interface Orders {
  [key: string]: OrderItem; // Order ID as the key
}

interface OrderItem {
  tq: number;
  li: string;
  [key: string]: number | string | DepartmentData; // Allow additional properties like departments
}
interface DepartmentData {
  woh: number;
  mfg: number;
  int: number | null;
  out: number;
}

interface ApiResponseItem {
  cc: string; // Main category code
  v: boolean; // Visibility flag
  cp?: number; // Main category property (optional since it will be added)
  hd: string; // Header description (will be set to the name of cc)
  cla: string; // Class alignment (fixed value)
  scc: string; // Sub-channel code (will be set to the name of cc)
  ch?: ApiResponse[]; // Array of channel items
  pinned?: string; // Pin property
  dt?: string;
}

const APIFilterConfig = {
  filSecVisConfig: {
    Prod_OverAll_BMReport: {
      mjr: false,
      or: true,
      res: true,
      cus: true,
    },
  },
};

const OverallBmReport = () => {
  const { mutateAsync: getOverallBMReportData} = useGetOverAllBMReport();
  const { mutateAsync: getBOMExplosionData /*isLoading :BombDataLoading*/ } =
    useGetBOMExplosionData();
  const { mutateAsync: getDBRsettingsData} = useGetDBRsettingsData();
  const { mutateAsync: getHighAgeingData, isLoading: isHighAgeingData } = useGetHighAgeingData();
  const { mutateAsync: getDeptWiseWipData, isLoading: isDeptWiseWipData} = useGetDeptWiseWipData();
  const { mutateAsync: getPoogIRemarks } = useGetPoogiRemarks();
  const { mutateAsync: getUIConfigData } = useGetUIConfigData();
  // const { screenHeight } = useViewPort();
  const refGraph2 = useRef<any>(null);
  const allotementRef = useRef<any>(null);

  const [coldefs, setColdef] = useState<any>();

  const [gridData, setGridData] = useState<any>();
  const [gridDataCount, setGridDataCount] = useState<number>(0);
  const rowsSelected = useRef(false);
  const [isRemarkHistoryOpen, setIsRemarkHistoryOpen] =useState<boolean>(false);
  const [remarkHistory, setRemarkHistory] = useState<any>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const cache = useRef<any>({});
  // for save and reset
  const [isReset, setIsReset] = useState<any>();
  const [columnState, setColumnState] = useState<any>();
  const [masterUIConfig, setMasterUIConfig] = useState([]);
  const [isPivot, setIsPivot] = useState<any>(false);
  const [userConfigFetched, setUserConfigFetched] = useState<any>(false);
  const [orderClosingEnable, setorderClosingEnable] = useState<any>();
  const { getGroupedColDef, groupedColDefsRef } = useColDef();

  const { user } = useUserData(); 
  const [masterSelectedRowData, setMasterSelectedRowData] = useState<any>(
    () => {
      return [];
    }
  );
  const [deptWiseWipData, setDeptWiseWipData] = useState<any>();
  
  const [deptName, setDeptName] = useState<any>([]);
  const [isOrderElapsedGrid, setIsOrderElapsedGrid] = useState<boolean>(false);
  const [filterData, setFilterData] = useState({});
  const [isGridLoading, setIsGridLoading] = useState(false);
  const [showExcelModal, setShowExcelModal] = useState(false);
  

  const { mutateAsync: getPageWiseFilterData /*isLoading*/ } =
  useGetFilterData();
  const {
    state: currFilter,
    setState: setCurrFilter,
    onFilterRemove,
    isFilterOpen,
    isMfgSelected,
    onAddFilter,
    onApplyFilter,
    toggleFilter,
    appliedFilters,
  } = useFilter(
    filterData,
    APIFilterConfig.filSecVisConfig.Prod_OverAll_BMReport
  );
  const [highAgeing, sethighAgeing] = useState<any>();
  const [tempColdef, setTempColdef] = useState<any>();
  const [bomHeader, setBomHeader]= useState([])
  const [bomActive, setBomActive] = useState<any>(undefined);
  const ReportName='BomExplosion'
  const { mutateAsync: getUserUIConfigData, isLoading: isGetStateLoading } =
    useGetUserUIConfigData();
  const { mutateAsync: updateUserUIConfigData, isLoading: isUpdateUserConfig } =
    useUpdateUserUIConfigData();
  const {
    mutateAsync: getShortOrderCompleteOrder,
    isLoading: isShortOrderCompleteOrder,
  } = useShortOrderCompleteOrder();
  const themeUi = user?.user?.theme_ui; 
  const feature_permission = user?.feature_permission || [];
  const canShowOrderClosing = feature_permission.includes("Order_Closing");

  const dispatch = useDispatch();
  const [userPageSize, setUserPageSize] = useState<any>();

  useEffect(() => {
    try {
      getOverallBMReportData({ page: 1, appliedFilters, analytics: 1 }).then(
        (data) => {
          const response: any = data?.data?.data;
          if (response) {
            const analytics = modifyAnalyticsData(response);
            dispatch(BM_REPORT_ANALYTICS(analytics));
          }
        }
      );
    } catch (e) {
      dispatch(BM_REPORT_ANALYTICS([]));
    }
  }, []);

  useEffect(() => {
    if (coldefs) {
      const tempcoldeflatest = _.cloneDeep(coldefs);
      tempcoldeflatest.shift();
      tempcoldeflatest.shift();
      setTempColdef(tempcoldeflatest);
    }
  }, [coldefs]);


  const onOpenRemarkHistory = async (data: any) => {
    // Function implementation for remark history
    try {
      const RemarkHistory = await getPoogIRemarks(data.ok);
      if (RemarkHistory.data?.data === "No remarks are present for the order") {
        data.rm = [];
      } else {
        data.rm = RemarkHistory.data?.data;
      }
      setRemarkHistory(data.rm);
      setIsRemarkHistoryOpen(true);
    } catch (e) {
      console.log(e);
    }
    setIsRemarkHistoryOpen(true);
  };

  const getSystemType = async () => {
    try {
      const DBRSettingsData: any = await getDBRsettingsData();
      const DBRSettings = DBRSettingsData.data?.data;
      if (DBRSettings && DBRSettings.length) {
        const BomFlag = DBRSettings?.find((data: any) => data.flag === "BOMActive" && data.value == 1);
        if (BomFlag) {
          setBomActive(true)
        }
        else {
          setBomActive(false)
        }
        setorderClosingEnable(canShowOrderClosing);
        getFilterData();
      } else {
        getFilterData();
      }
    } catch (e) {
      console.error(e);
    }
  };

   useEffect(()=>{
    if(bomActive != undefined){
      setColumnDef();
    }
    },[bomActive])

const setColumnDef = async () => {
  try {
    const reportName = "BMReport";
    const response = await getUIConfigData(reportName);
    getGroupedColDef(response);

    const gridOptions = {
      bomActive: bomActive,
      orderClosingEnable: canShowOrderClosing,
      canAddComments: false,
      onOpenRemarkHistory: onOpenRemarkHistory,
    };

    const colDefsData = createDynamicColumnDefs(response?.data?.data || [], gridOptions,user);

    setColdef(colDefsData);
  } catch (e) {
    console.log(e);
    notifyError("Failed to build grid columns.");
  }
};

 interface ActionOption {
    value: string;
    label: string;
  }

  const actionOptions: ActionOption[] = [
    { value: "Short Close", label: "Short Close" },
    { value: "Complete Close", label: "Complete Close" },
  ];

  // const [selectedRowCount, setSelectedRowCount] = useState(0);
  const [selectedAction, setSelectedAction] = useState<any>(null);
  const [textAction, setTextAction] = useState<any>();

  const [totalOrderCount, setTotalOrderCount] = useState<any>(0);
  const [isCheckboxChecked, setIsCheckboxChecked] = useState(false);


  // AFTER (The fix)
const onCheckBoxToggle = (e: any) => {
  setIsGridLoading(true);
  const isChecked = e.target.checked;
  setIsCheckboxChecked(isChecked);
  
  if (refGraph2.current?.api) {
    if (isChecked) {
      // This method respects the current filter and only selects visible rows
      refGraph2.current.api.selectAllFiltered();
    } else {
      // This deselects all rows (filtered or not), which is usually the desired behavior on uncheck
      refGraph2.current.api.deselectAll();
      setSelectedAction(null);    
    }
  }
};

  const toggleCheckBox = () => {
    const selectedNodes = refGraph2?.current?.api?.getSelectedRows();
    const totalRows = refGraph2?.current?.api?.getDisplayedRowCount();
    
    // Only update checkbox state if all filtered rows are selected
     setIsCheckboxChecked(totalRows > 0 && selectedNodes?.length === totalRows);

  };
 
const handleActionChange = (option: any) => {
  setSelectedAction(option);

  if (!option) {
    return;
  }

  // Updating across all pages
  setMasterSelectedRowData((updated: any) =>
    updated.map((masterRow: any) => ({
      ...masterRow,
      oca: option.value
    }))
  );

  // updating currently visible rows
  if (refGraph2.current?.api) {
    const currentlyVisibleSelectedRows = refGraph2.current.api.getSelectedRows();
    const visibleSelectedKeys = new Set(currentlyVisibleSelectedRows.map((row: any) => row.ok));

    setGridData((currentGridData: any) =>
      currentGridData.map((row: any) => {
        if (visibleSelectedKeys.has(row.ok)) {
          return { ...row, oca: option.value };
        }
        return row;
      })
    ); 
  }
};



  
  const updateActionAPI = async (action: string, order_ids: any) => {
    try {
      if (action === "undo") {
        const response = await getShortOrderCompleteOrder({
          order_keys: order_ids,
        });
        return response;
      } else {
        const response = await getShortOrderCompleteOrder({
          close_type: action === "Short Close" ? "0" : "1",
          order_keys: order_ids,
        });
        return response;
      }
    } catch (error) {
      console.log(error);

      throw error;
    }
  };

  const [showModal, setShowModal] = useState(false); // Renamed state

  const [shortCloseTracker, setShortCloseTracker] = useState(0)
  const [completeCloseTracker, setCompleteCloseTracker]=useState(0)

  const handleRightArrowClick = () => {
    setShowModal(true);
    setTextAction(selectedAction?.label);
  
    if (Array.isArray(masterSelectedRowData)) {
      let shortCloseCount = 0;
      let compCloseCount = 0;
      
      //  orders that haven't been closed yett
      const openOrders = masterSelectedRowData.filter(
        (item) => 
           item?.ot !== "MTA" &&
          (item?.ct === null || item?.ct === undefined)      );
      
      masterSelectedRowData.forEach((item) => {
       const isNotMta = item?.ot !== "MTA";
      const isNotClosed = item.ct === null || item.ct === undefined;

        if (isNotMta && isNotClosed) {
        if (item?.oca === "Short Close") {
          shortCloseCount++;
        } else if (item?.oca === "Complete Close") {
          compCloseCount++;
        }
      }
    });
      
      setShortCloseTracker(shortCloseCount);
      setCompleteCloseTracker(compCloseCount);
      
      const okValues = openOrders
        .map((item: any) => item?.ok)
        .filter((value: any) => value !== undefined);
    
      setTotalOrderCount(okValues.length);
    }
    
  };
  
  const handleRightArrowClick1 = (action: string, orderId: string) => {
    setShowModal(true); // Open the modal
    setTextAction(action);
    setTotalOrderCount(orderId);
  };

  const handleModalClose = () => {
    setShowModal(false); // Close the modal
  };

const handleModalConfirm = async (orderId?: any, actionText?: any) => {
    try {
      setShowModal(false);

      if (orderId && orderId !== "") {
        const response = await updateActionAPI(actionText, [orderId]);

        if (response?.status === 200) {
          notifySuccess("Order closed successfully!");

          const newGridData = [...gridData];
          newGridData.forEach((ele: any) => {
            if (!_.isEmpty(ele)) {
              if (ele.ok === orderId) ele.ct = actionText;
            }
          });
          setGridData(newGridData);
        } else {
          notifyError("Something went wrong!");
        }
      } else if (Array.isArray(masterSelectedRowData)) {
        const okValues = masterSelectedRowData
          .filter((item) => item?.ot !== "MTA")
          .map((item) => (item.ct === null || item.ct === undefined || item.ct === "") ? item?.ok : undefined)
          .filter((value) => value !== undefined);

        if (okValues.length === 0) {
          notifyError("No eligible orders to close.");
          return;
        }

        const response = await updateActionAPI(selectedAction.value, okValues);

        if (response?.status === 200) {
          const newGridData = [...gridData];
          newGridData.forEach((ele: any) => {
            if (!_.isEmpty(ele)) {
              if (okValues.includes(ele.ok)) {
                ele.ct = actionText || selectedAction.value; 
              }
            }
          });
          setGridData(newGridData);
          setMasterSelectedRowData([]); 
          setSelectedAction(null);
          setIsCheckboxChecked(false); 
          notifySuccess("Orders closed successfully!");
        } else {
          notifyError("Something went wrong!"); 
        }
      }
    } catch (error) {
      console.error("Failed to perform action:", error);
    }
  };


  const undoClicked = async (props: any, orderId: string) => {
    try {
      const response = await updateActionAPI("undo", [orderId]);
      if (response?.status === 200) {
        notifySuccess("Order retrived succesfully! ");
        const newGridData: any = [];
        props.api.forEachNode((node: any) => {                            
          newGridData.push(node.data);
        });

        newGridData?.forEach((ele: any) => {
          if (!_.isEmpty(ele)) {            
            if (ele.ok === orderId) {
              ele.ct = null;
              ele.oca = null;
            }
          }
        });
        setGridData(newGridData);
      } else {
        notifyError("Something went wrong!");
      }
    } catch (error) {
      console.log("Error occurred while updating action:", error);
      throw error;
    }
  };

  const isRightArrowEnabled =
    (isCheckboxChecked  || masterSelectedRowData.length > 1) && 
    selectedAction != null;


  const DropdownArrowIcon = () => (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width="24"
      height="24"
      fill="none"
    >
      <path d="M7 10l5 5 5-5H7z" fill="currentColor" />
    </svg>
  );

  const OrderCloseHeader: any = (
    <>
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          fontSize: "18px",
          fontWeight: "bold",
          gap: "15px",
        }}
      >
        {/* Checkbox and Select */}
        <div
          style={{
            borderRadius: "5px",
            background: "white",
            padding: "10px 30px",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            boxShadow: "rgba(133, 132, 132, 0.247) -5px 4px 10px",
            opacity: isPivot ? 0.5 : 1,
            pointerEvents: isPivot ? 'none' : 'auto',
            gap: "10px",
          }}
        >
          <InputCheckBox
            onChange={onCheckBoxToggle}
            type="checkbox"
            theme={themeUi}
            disabled={isPivot}
            checked={isCheckboxChecked}
          />
          <VFSelect
            options={actionOptions}
            themeUi={themeUi}
            icon={DropdownArrowIcon}
            disabled={!isCheckboxChecked && masterSelectedRowData.length < 2}
            placeholder="Select Action"
            value={selectedAction}
            onChange={handleActionChange}
          />
        </div>

        {/* Right Arrow - Disabled if Checkbox is Unchecked */}
        <VFButton
          data-testid={"isReleaseBtn"}
          onClick={() => handleRightArrowClick()}
          themeUi={themeUi}
          disabled={false}
          style={{
            cursor: isRightArrowEnabled && !isPivot ? "pointer" : "not-allowed",
            height: "50px",
            width: "60px",
            borderRadius: "3px",  
            opacity: isRightArrowEnabled && !isPivot ? 1 : 0.5, 
            pointerEvents: isRightArrowEnabled && !isPivot ? "auto" : "none",
            }}
        >
          <img
            src="/assets/img/rightArrowHorizontal.svg"
            height={13}
            width={7}
          />
        </VFButton>
      </div>
    </>
  );


  const onSelectChange = (props: any, option: any, index: number) => {
  const updatedData = { ...props.data, oca: option.value };
  props.node.setData(updatedData); 
  props.api.refreshCells({ rowNodes: [props.node], columns: ['oca'], force: true });


  setMasterSelectedRowData((currentMasterData:any) => 
    currentMasterData.map((row:any) => 
      row.ok === props.data.ok ? { ...row, oca: option.value } : row 
    )
  );
};

  const DropDownCellRenderer = (props: any) => {

    if (props.data?.ot === "MTA") {
    return null; 
  }
  
    return (
      <>
        
        {!_.isEmpty(props.data) && props.data?.ct === null ? (
          <>
          <VFSelect
              options={actionOptions}
              themeUi={themeUi}
              icon={DropdownArrowIcon}
              placeholder="Select Action"
              disabled={!props.node.selected}
              value={
                props.node.selected ? 
                  actionOptions.find((opt) => opt.value === props.data?.oca) :
                  null}
              onChange={(option: any) => {
              if (option) {
              onSelectChange(props, option, props.node.rowIndex);
              }
            }}
          />

            <div
              style={{
                cursor:
                  props.data?.oca && props.node.selected
                    ? "pointer"
                    : "not-allowed",
                opacity: props.data?.oca && props.node.selected ? 1 : 0.5,
                background:
                  props.data?.oca && props?.node?.selected
                    ? `linear-gradient(to right, ${ColorsMTO.darkPink.code}, ${ColorsMTO.Pink.code})`
                    : "#ccc",
                height: "43px",
                width: "59px",
                borderRadius: "4px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              data-testid="isReleaseBtn"
              onClick={() => {
                if (props.data?.oca && props.node.selected) {
                  handleRightArrowClick1(
                    props.data.oca === "Short Close"
                      ? "Short Close"
                      : "Complete Close",
                    props.data.ok
                  );
                }
              }}
            >
              <img
                src="/assets/img/rightArrowHorizontal.svg"
                height={13}
                width={7}
                alt="Right Arrow"
              />
            </div>
          </>
        ) : (
          <>
          {!_.isEmpty(props.data) && 
            <div
              style={{
                justifyContent: "space-between",
                display: "flex",
                alignItems: "center",
                gap: "5px",
                margin: "10px",
              }}
            >
                {
                  props?.data?.ct &&
                  <>
                    <p>{props.data?.ct}</p>
                    <div
                      onClick={() => {
                        undoClicked(props, props.data.ok);
                      }}
                      style={{
                        marginLeft: "10px",
                        display: "flex",
                        alignItems: "center",
                        cursor: "pointer",
                      }}
                    >
                      <img
                        style={{
                          transform: "rotateY(180deg)",
                          margin: "4px",
                          cursor: "pointer",
                        }}
                        src="/assets/img/VectorFLOW/reset.svg"
                        alt="Undo"
                        title="Undo"
                        height={14}
                        width={14}
                      />
                    </div>
                  </>
                }
              
            </div>
          }
          </>
          )}
          
      </>
    );
  };

  const excelColorArr = ["Black", "Red", "White", "Green", "Yellow", "Blue"]


  const getFilterData = async () => {
    try {
      const response = await getPageWiseFilterData({
        page_name: FilterPageName.Prod_OverAll_BMReport,
      });
      setFilterData(response?.data.data);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    getSystemType();
  }, []);

  const customCellRenderers = useMemo(
    () => ({
      colorCellRenderer: BPPRenderer,
      AgeingCellRenderer: AgeingCellRenderer,
      RemarkHistoryRenderer: RemarkHistoryRenderer,
      DropDownCellRenderer: DropDownCellRenderer,
      customHeaderCheckbox: CustomHeaderCheckbox,
    }),
    []
  );

  const sideBar = useMemo(() => {
    return {
      toolPanels: ["columns"],
    };
  }, []);

   useEffect(()=>{
         if(coldefs && bomActive ){
           getBOMUIConfigData()
         }
       }, [coldefs,bomActive])
     
  
        const getBOMUIConfigData = async () => {
          try {
            const response = await getUIConfigData (ReportName);
            setBomHeader(response?.data?.data)
          } catch (err) {
            console.error(err);
            notifyError("Something Went Wrong!");
          }
        };
      
        const columnBomDefs = useMemo(() => {
          return getColumnDefinations(bomHeader);
        }, [bomHeader]);

  const getInitialGridData = async (currentPage: number, pageSize?: any, isExcelExport = false, isBomExplosion=0) => {
    //excellll

    if (isExcelExport) {
      notifyLoader("Preparing data for export...");
      const headersdata = refGraph2?.current?.api?.getColumnState();
      const formatedFilters = formatFilterJSON(appliedFilters);


      const body = getBodyForExcelExport({headersdata,filterData: formatedFilters,groupedColDefsRef})
          try{
              const response = await getOverallBMReportData({body,isExcelExport : 1,page:currentPage,report_name : FilterPageName.Prod_OverAll_BMReport, page_size: pageSize || userPageSize,isBomExplosion})
              if(response.status == 200){//1,userpage,true,0
                DownloadExcel(response,FilterPageName.Prod_OverAll_BMReport)
                notifySuccess("Excel exported successfully!");
              }else{
                notifyError("Error exporting Excel!");
              }
            }catch(e){
              console.error("Error exporting Excel", e);
              notifyError("Error exporting Excel!");
            }
      
      
    } else {
    try {
      setIsGridLoading(true);
      const formatedFilters = formatFilterJSON(appliedFilters);

      const gridData = await getOverallBMReportData({
        page: currentPage,
        appliedFilters: formatedFilters,
        user,
        page_size: pageSize || userPageSize
      });
      if (!gridData?.data?.data || gridData?.data?.data?.length === 0) {
        setGridDataCount(0);
        setGridData([]);
        setIsGridLoading(false);
        return;
      }
      const modifiedGridData = gridData?.data?.data?.results.map(
        (data: any) => {
          return {
            ...data,
            oca: null,
          };
        },
        []
      );
      setGridData(modifiedGridData);
      setGridDataCount(gridData?.data?.data?.count);
      setIsGridLoading(false);
    } catch (e) {
      notifyError("No Records found for the selected filter!");
      setGridDataCount(0);
      setGridData([]);
      setIsGridLoading(false);
      console.log(e);
    }
  }
  };


  const handlePageChange = useCallback((currPage: number) => {
    setCurrentPage(currPage);
    setIsCheckboxChecked(false);
    getInitialGridData(currPage);
  }, [getInitialGridData]);

  const savePageSize = (pageSize: any) => {
    if (pageSize) {
      setCurrentPage(1);
      setUserPageSize(pageSize);
      handleSaveClick(undefined,pageSize);
      getInitialGridData(1, pageSize);
    } else {
      notifyError("Invalide page size");
    }
    
  }

  const extractDepartmentNames = (orders: Orders): string[] => {
    const departmentNames: Set<string> = new Set();

    // Iterate over each order
    Object.values(orders).forEach((orderItem) => {
      // Iterate over each property in the order item
      Object.keys(orderItem).forEach((key) => {
        // Check if the property is a department (i.e., not 'tq' or 'li')
        if (key !== "tq" && key !== "li") {
          departmentNames.add(key);
        }
      });
    });

    // Convert Set to Array and return
    return Array.from(departmentNames);
  };

  useEffect(() => {
    if (allotementRef.current) allotementRef.current.reset();
  }, [rowsSelected.current]);

  const fetchDeptWiseWiphData = async (selectedOrderKeys: any) => {
    try {
      notifyLoader("Loading");
      const DeptWiseWipData = await getDeptWiseWipData(selectedOrderKeys);
      const highAgeingData = await getHighAgeingData(selectedOrderKeys);
      sethighAgeing(highAgeingData?.data?.data);
      setDeptWiseWipData(DeptWiseWipData?.data?.data);
      const departmentNames = extractDepartmentNames(
        DeptWiseWipData?.data?.data
      );
      departmentNames.sort();
      setDeptName(departmentNames);
      notifySuccess("Fetched");
    } catch (error) {
      notifyError("Failed to fetch data");
    }
  };

  const getSelectedRow = () => {
    const selectedData = refGraph2.current?.api.getSelectedRows();
    rowsSelected.current = selectedData.length > 0;
    
    // Use efficient data structures
    const selectedKeys = new Set(selectedData.map((item: any) => item.ok));
    let updated = false;
  
    // Create a map for quick access to mergedData items
    const mergedDataMap = new Map(masterSelectedRowData.map((item: any) => [item.ok, item]));
   
    selectedData.forEach((newItem: any) => {
      if (!mergedDataMap.has(newItem.ok)) {

        mergedDataMap.set(newItem.ok, newItem);
        updated = true;
      }
    });
    // Filter out unselected items
     gridData?.forEach((item: any) => {
       if (item && item.ok && !selectedKeys.has(item.ok) && mergedDataMap.has(item.ok)) {
        item.oca = null; 
        mergedDataMap.delete(item.ok);
        updated = true;

      }

     });    
    
    // Only update state if there's a change
    if (updated) {
      setMasterSelectedRowData(Array.from(mergedDataMap.values()));
    }
  
    toggleCheckBox();  // Ensure checkboxes are correctly toggled
    refGraph2.current.api.refreshCells();  // Refresh cells in the grid
    setIsGridLoading(false);
  };

  useEffect(() => {
    if (masterSelectedRowData.length > 0) {
      const selectedOrderKeys: orderkeyObj[] = [];
      masterSelectedRowData?.map((ele: any) => {
        selectedOrderKeys.push(ele.ok);
      });

      fetchDeptWiseWiphData(selectedOrderKeys);
      setIsOrderElapsedGrid(true);
    } else {
      setDeptWiseWipData("");
      setIsOrderElapsedGrid(false);
    }
  }, [masterSelectedRowData]);

  const existsInSelected = (reqOid: string): boolean => {
    for (let index = 0; index < masterSelectedRowData.length; index++) {
      const element: any = masterSelectedRowData[index];
      if (element.ok === reqOid) {
        return true;
      }
    }
    return false;
  };

  const onFirstDataRendered = (params: any) => {
    const nodesToSelect: IRowNode[] = [];
    params.api.forEachNode((node: any) => {
      if (node.data && node.data.ok && existsInSelected(node.data.ok)) {
        node.data.Remark = masterSelectedRowData[0].Remark;
        for (let index = 0; index < masterSelectedRowData.length; index++) {
          const element = masterSelectedRowData[index];
          if (element.ok === node.data.ok) {
            node.data.Remark = element.Remark;
            node.data.oca = element.oca;
          }
        }
        nodesToSelect.push(node);
      }
    });
    params.api.setNodesSelected({ nodes: nodesToSelect, newValue: true });
    params.api.refreshCells();
    toggleCheckBox();
  };

 
const onPivotModeChanged = (event: any) => {
  const isPivotOn = event.api.isPivotMode();
  setIsPivot(isPivotOn);
  
  event.api.getColumnApi()?.setColumnVisible('chckbx', !isPivotOn);
};

      const detailCellRendererParamsConfig = useMemo(() => {
          const itemNameColumnDef = columnBomDefs.find((a: any) => a.colId === "ItemName");
        
          const config = {
            masterDetail: bomActive?true:false,
            detailCellRendererParams: {
              suppressMenu: true,
              detailGridOptions: {
                rowHeight: 28,
                headerHeight:30,
                // domLayout: "autoHeight",
                autoGroupColumnDef: {
                  headerName:itemNameColumnDef?.headerName,
                  cellRendererParams: {
                    suppressCount: true,
                  },
                },
                columnDefs:columnBomDefs.filter((col: any) => col.colId !== "ItemName"),
                defaultColDef: {
                  flex: 1,
                  suppressMenu: true,
                  cellStyle: {
                    fontSize: "16px",
                    display: "flex",
                    alignItems: "center",
                  },
                },
      
                treeData: true,
                getDataPath: (data: any) => {
                  return data.path;
                },
              },
              getDetailRowData: async (params: any) => {
                if (!_.isEmpty(params.data)) {                
                  if (cache.current[`${params.data.oid}-${params.data.lid}`]) {
                    params.successCallback(
                      cache.current[`${params.data.oid}-${params.data.lid}`]
                    );
                    return;
                  }
                  const data = await getBOMExplosionData({
                    orderId: params.data.oid,
                    lineId: params.data.lid,
                  });
                  cache.current[`${params.data.oid}-${params.data.lid}`] = data.data.data;
                  params.successCallback(data?.data?.data);
                  return;
                }
              },
            },    
          };
          return config;
        }, [columnBomDefs, bomHeader]);

  const agGridProps: AgGridReactProps = {
      tooltipShowDelay: 0,
      tooltipTrigger: "focus",
      gridOptions: {
        rowHeight: 50,
        getRowStyle: (params: any) => {
          return {
            background: params.node.rowIndex % 2 === 0 ? "#EBEBEB" : "#F7F7F7",
          };
        },
        rowSelection: "multiple",
        suppressRowClickSelection: true,
        enableBrowserTooltips: true,
        enableRangeSelection: true,
        components: customCellRenderers,
        pagination: true,
        // pivotMode: false,
        defaultColDef: {
          enablePivot: true,
          filter: "agTextColumnFilter",
          floatingFilter: true,
          //suppressFiltersToolPanel:true,
          cellStyle: {
            textAlign: "center",
            //'height': '50px',
            //"fontStyle": "Roboto",
            //"fontVariant": "normal",
            fontSize: "18px",
            fontFamily: "Roboto",
            whiteSpace: "nowrap",
            resizable: "true",
            color: "#000",
          },
          // floatingFilterComponentParams: {
          //   // suppressFilterButton: true,
          // },
        },
      },
      sideBar: sideBar,
      masterDetail: true,
      //detailCellRenderer: RowGroupRenderer,
      //detailCellRendererParams:RowGroupRenderer,
      paginationAutoPageSize: true,
      enterNavigatesVertically: true,
      enterNavigatesVerticallyAfterEdit: true,
      groupDefaultExpanded: 0,
      // onSelectionChanged: debounce(getSelectedRow, 1000),
      onSelectionChanged: getSelectedRow,
      onRowDataUpdated: onFirstDataRendered,
      onColumnPivotModeChanged: onPivotModeChanged,
    };

  useEffect(() => {
    if (Object.keys(appliedFilters).length && userConfigFetched) {
      if (currentPage != 1) {
        setCurrentPage(1);
      } else {
        getInitialGridData(currentPage);
      }
    }
  }, [appliedFilters, userConfigFetched]);

  const tempGridRef = useRef<any>(null);
  const [tempGridData, setTempGridData] = useState<any>(undefined);
  const [isExcelLoading, setIsExcelLoading] = useState<boolean>(false);



  const onExcelExport = () => {

    const gridApi = refGraph2.current?.api;

    if (!gridApi) {
      // Grid might not be ready, notify the user
      notifyError("Grid is not ready, please wait.");
      return;
    }

    const isRowGroupingActive = gridApi.getRowGroupColumns().length > 0;
    const isValueActive = gridApi.getValueColumns().length > 0;


    if (isPivot || isRowGroupingActive || isValueActive) {
     refGraph2.current?.api?.exportDataAsExcel({
          fileName: ExcelExportName.OverallBMReport ,
          sheetName: ExcelExportName.OverallBMReport,
        });
    } else {
      if (bomActive) {
        setShowExcelModal(true)
      } else {
        getInitialGridData(1, userPageSize, true, 0);
      }
    }
  };

  const getUserColumnConfig = async () => {
    try {
      const data = await getUserUIConfigData({
        un: user.user.name,
        rn_id: UIGridCode.ProdOverallBMReport,
      });

      const newConfig = data?.data?.data?.length ? JSON.parse(data?.data?.data?.[0]?.columns_settings) || [] : [];
      setUserPageSize(newConfig.pageSize ? Number(newConfig.pageSize) : undefined);
      setColumnState(newConfig.cs);
      setIsPivot(newConfig.pivot);
      setUserConfigFetched(true);

      if (!data) {
        console.error("Failed to apply column state");
      }
    } catch (error) {
      console.error(error);
    }
  };

  const handleSaveClick = async (coldefs?: any,page_size?:any) => {
    try {
      if (coldefs) {
        //reset case
        const fullConfig = { pivot: false, cs: coldefs, pageSize: userPageSize };
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.ProdOverallBMReport,
          cs: JSON.stringify(fullConfig),
        };

        await updateUserUIConfigData([payload]);
        setColumnState([...coldefs]);
        setIsPivot(false);
      } else if (page_size) {
        const config = columnState;
        const fullConfig = { pivot: isPivot, cs: config, pageSize: page_size };

        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.ProdOverallBMReport,
          cs: JSON.stringify(fullConfig),
        };
        await updateUserUIConfigData([payload]);
      } else {
        if (refGraph2?.current?.api) {
          const config = refGraph2.current.api.getColumnState();
          const isPivot = refGraph2.current?.api.isPivotMode();
          const fullConfig = { pivot: isPivot, cs: config, pageSize: userPageSize };

          // setColumnState(config);

          const payload = {
            un: user.user.name,
            rn_id: UIGridCode.ProdOverallBMReport,
            cs: JSON.stringify(fullConfig),
          };
          await updateUserUIConfigData([payload]);
          await getUserColumnConfig();
        }
      }
      notifySuccess("Changes saved successfully");
    } catch (error) {
      console.error(error);
      notifyError("Error saving changes");
    }
  };

  const handleResetClick = () => {
    setIsReset(true);
  };

  useEffect(() => {
    if (isReset) {
      handleSaveClick(masterUIConfig);
      setIsReset(false);
    }
  }, [isReset]);

  useEffect(() => {
    if (refGraph2?.current?.api) {
      setMasterUIConfig(refGraph2?.current?.api.getColumnState());
      getUserColumnConfig();
    }
  }, [coldefs]);

  useEffect(() => {
    if (refGraph2?.current && columnState?.length) {
      const result = refGraph2.current.api.applyColumnState({
        state: columnState,
        applyOrder: true,
      });
      // refGraph2.current?.api.autoSizeAllColumns()
      const applyPivot = refGraph2.current?.api.setGridOption(
        "pivotMode",
        isPivot
      );
      refGraph2.current.api.autoSizeAllColumns()
      if (!result || !applyPivot) {
        console.error("Failed to apply column state");
      }
    }
  }, [columnState,refGraph2,refGraph2.current]);

  const { data: apiResponseData /*isLoading, refetch*/ } = useGetDate();

  const date = apiResponseData?.data?.data;

  const excelStyles = useMemo(() => 
    excelColorArr.map((color) => ({
      id: color,
      font: { color: color === "White" ? "000000" : "#ffffff" },
      interior: {
        color: color === "White"  ? "#A8A8A8" : ColorsMTO[color as keyof typeof ColorsMTO]?.code,
        pattern: 'Solid'
      }
    }))
  , []);

  const handleExcelConfirm = () => {
    setShowExcelModal(false);   
    getInitialGridData(1, userPageSize, true, 1);
  };

  const handleExcelCancel = () => {
    setShowExcelModal(false);
    getInitialGridData(1, userPageSize, true, 0);
  };
  

  return (
    <BMDepWrapper>
      <BMDepHeaderWraper>
        <MTOActionToolBar
          comp={"OverallBMReport"}
          isAddFilterButton
          isExcelExport
          themeUi={themeUi}
          onExcelExportClick={onExcelExport}
          isFilterOpen={isFilterOpen}
          onAddFilter={onAddFilter}
          toggleFilter={toggleFilter}
          onApplyFilter={onApplyFilter}
          multiFilter={currFilter}
          WIPFilter={orderClosingEnable ? OrderCloseHeader : null}
          setMultiFilter={setCurrFilter}
          onFilterRemove={onFilterRemove}
          isMfgSelected={isMfgSelected}
          handleSaveClick={handleSaveClick}
          handleResetClick={handleResetClick}
        />
      </BMDepHeaderWraper>
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          fontSize: "14px",
          fontWeight: "bold",
          fontFamily: "Roboto",
          marginTop: "10px",
        }}
      >
        <p>{date && date.length ? moment(date).format("D MMM YYYY") : " "}</p>
      </div>
      
        <BomExcelModal
        open={showExcelModal}
        onClose={() => setShowExcelModal(false)}
        onConfirm={handleExcelConfirm}
        onCancel={handleExcelCancel}
        themeUi={themeUi}
        headerText={"Excel Export"}
        messageText={"Do you want to download Excel with BOM Data?"}
                
      />
      
      {(isGridLoading ||
        isExcelLoading ||
        isGetStateLoading ||
        isShortOrderCompleteOrder ||
        isUpdateUserConfig ||
        isDeptWiseWipData || 
        isHighAgeingData) && <OverlayLoader />}

      <HorizontalViewWrapper style={{ marginTop: "0", paddingLeft:"25px" }}>
        <BTRTableWrapper
          style={{
            height: rowsSelected.current ? "120vh" : "75vh",
            margin: "0",
          }}
        >
          <Allotment vertical={true} separator={true} ref={allotementRef}>
            <Allotment.Pane
              preferredSize={rowsSelected.current ? "45%" : "70%"}
            >
              <BTRAllomentSection>
                <GridView
                  reference={refGraph2}
                  agGridProps={agGridProps}
                  columDef={coldefs}
                  convercolumnDef={gridData}
                  handlePageChange={handlePageChange}
                  saveBtn={false}
                  totalRow={gridDataCount}
                  currentPage={currentPage}
                  customPageSize={true}
                  savePageSize={savePageSize}
                  userPageSize = {userPageSize}
                  detailCellRendererParamsConfig={detailCellRendererParamsConfig}
                />
                {/* This Grid is only for the user to download the excel report */}
                <div style={{ display: "none" }}>
                  <GridView
                    reference={tempGridRef}
                    agGridProps={agGridProps}
                    columDef={tempColdef}
                    convercolumnDef={tempGridData}
                    handlePageChange={handlePageChange}
                    saveBtn={false}
                    totalRow={gridDataCount}
                    currentPage={currentPage}
                    excelStyles={excelStyles}
                    savePageSize={savePageSize}
                    userPageSize = {userPageSize}
                    detailCellRendererParamsConfig={detailCellRendererParamsConfig}
                  />
                </div>
              </BTRAllomentSection>
            </Allotment.Pane>

            <Allotment.Pane
              preferredSize={rowsSelected.current ? "55%" : "30%"}
            >
              <VFWrapper>
                <BTRAllomentSection>
                  <OrderElapsedGrid
                    isTrue={isOrderElapsedGrid}
                    data={deptWiseWipData}
                    deptName={deptName}
                    selectedOrderCount={masterSelectedRowData.length}
                    highAgeingdata={highAgeing}
                  />
                </BTRAllomentSection>
              </VFWrapper>
            </Allotment.Pane>
          </Allotment>
        </BTRTableWrapper>

        <ConfirmationModal
          key={2}
          isOpen={showModal}
          onClose={handleModalClose}
          onConfirm={handleModalConfirm}
          title={textAction}
          // message="Are you sure?"
          actionText={textAction}
          orderCount={totalOrderCount}
          completeCloseTracker={completeCloseTracker}
          shortCloseTracker={shortCloseTracker}
        />
      </HorizontalViewWrapper>

      <BPRRemarkHistoryModal
        data={remarkHistory}
        isOpen={isRemarkHistoryOpen}
        onClose={() => setIsRemarkHistoryOpen(false)}
      />
    </BMDepWrapper>
  );
};

export default OverallBmReport;
