import { AgCharts } from 'ag-charts-react';
import { GridOptions, IRowNode } from 'ag-grid-enterprise';
import { useEffect, useRef, useState } from 'react'
import VFTable from '../../Common/VFTable';
import { DownloadExcel, formatFilterJSON, getBodyForExcelExport, getColumnDefinations } from '../../../../../helpers/utils';
import AvailabilityCellRenderer from '../../../MTA/InsightsAndTrends/BTR/AvailabilityCellRenderer';
import ColorCellRenderer from '../../Common/ColorCellRenderer/ColorCellRenderer';
import { Button, Wrapper, BPRViewTableHeaderTab, InputCheckBox, SCTabHeader } from './DynamicReleaseManagement.styled';
import { useUserData } from '../../../../../context';
import MTOActionToolBar from '../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar';
import EditRouteModal from '../../Common/EditRouteModal';
import * as globalStyles from "../../../../../styles/global";
import ReleaseModal from './ReleaseModal';
import './styles.css'
import { useGetDynamicReleaseData, useGetDynamicReleaseExcelData } from '../../../../../VectorFlow/Services/MTO/Production/DynamicReleaseManagement';
import { notifyError, notifySuccess } from '../../../../../helpers/notify';
import OverlayLoader from '../../Common/Loader';
import VFPagination from '../../Common/VFPagination';
import { GridRef } from '../../../../../VectorFlow/types/MDM';
import { useGetUIConfigData } from '../../../../../VectorFlow/Services/MTO/Common/UIConfig';
import { FilterPageName, pagination, UIGridCode } from '../../Common/Enum';
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from '../../../../../VectorFlow/Services/MTO/Common/UserUIConfig'
import useFilter from "../../../../../hooks/useFilter";
import { useGetFilterData } from "../../../../../VectorFlow/Services/MTO/Common/CommonFilter";
import useColDef from '../../../../../hooks/useColDef';
import { ColorsMTO } from '../../Common/Colors';
import VFButton from '../../../../../components/VectorFLOW/commons/VFButton';
import BPPRenderer from '../../Common/BPRRenderer/BPPRenderer';
import { useGetDBRsettingsData } from '../../../../Services/MTO/Common/DBRSettings';
import { useNavigate } from 'react-router';
import VFWarningModal from '../../../../../components/VectorFLOW/commons/MTO/VFWarningModal';
import _ from 'lodash';
import CustomLegend from '../../Common/CustomLegend';

const APIFilterConfig = {
  filSecVisConfig: {
    "Prod_Dynamic_Release_Management" : {
      mjr : false,
      or: true,
      res: true,
      cus: true
    },
  }
};

const isApiLoading = (...loadingStates: boolean[]) => {
  return loadingStates.some(state => state);
};

const DynamicReleaseManagement = () => {
  interface InputData {
    [key: string]: {
      ccr_code: string;
      limit: number | 0;
      wip: number | 0;
      ccr_name: string;
      "Incremental WIP"?: number | 0;
      selected?: boolean;
      fol_gap: number | 0,
    };
  }
  interface OutputData {
    category: string[];
    "Released WIP": number;
    Limit: number;
    "Incremental WIP": number;
    selected: boolean;
    "CCR Name": string;
    "FOL Gap": number;
  }
  type ApiResponse = {
    status: number;
    data: { data: { results: any[] } };
  };
  const reportName = "DynamicReleaseManagement";
  const [currentGridRef, setCurrentGridRef] = useState<any>(null);
  const [columnState, setColumnState] = useState<any>([]);
  const [isReset, setIsReset] = useState<any>(undefined);
  const [colDef, setColDef] = useState([{}]);
  const refGrid = useRef<GridRef | any>(null)
  const [selectedRows, setSelectedRows] = useState<any>([]);
  const [rowRelease, setRowRelease] = useState(false);
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const [order_key, setOrder_Key] = useState('');
  const [table1, setTable1] = useState<any>(undefined);
  const [showReleaseModal, setShowReleaseModal] = useState(false)
  const { mutateAsync: getDBRsettingsData, isLoading: isDBRSettingData } = useGetDBRsettingsData();
  const { mutateAsync: getDynamicReleaseData, isLoading, isError, isSuccess } = useGetDynamicReleaseData();
  const { mutateAsync: updateUserUIReportConfigData, isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
  const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } = useGetUserUIConfigData();
  const { mutateAsync: getDynamicReleaseExcelData, isLoading: isDynamicReleaseExcelData } = useGetDynamicReleaseExcelData();
  const { mutateAsync: getPageWiseFilterData, isLoading: isGetFilterData } = useGetFilterData();
  const { mutateAsync: getUIConfigData, isLoading: isGetUIConfigData } = useGetUIConfigData();
  const [rowDataCount, setRowDataCount] = useState<any>([]);
  const [rowData, setRowData] = useState<any>([]);
  const [graphData, setGraphData] = useState<any>({});
  const [hide, setHide] = useState(false);
  const [showModal, setShowModal] = useState(false)
  const graph = useRef<any>();
  const [message, setMessage] = useState('');
  const [HeaderData, setHeaderData] = useState([]);
  const [filterData, setFilterData] = useState({});
  const [isDisabled, setIsDisabled] = useState<boolean>(true);
  const { colDefMap, getColDef } = useColDef();
  const [masterUIConfig, setMasterUIConfig] = useState([]);
  const userTheme = themeUi === 'REGALBLAZE';
  const backgroundColor = userTheme ? ColorsMTO.Orange.code : ColorsMTO.darkPink.code;
  const [finalGraphData, setFinalGraphData] = useState<any>([]);
  const [orderDetails, setOrderDetails] = useState<any>({});
  const [currentPage, setCurrentPage] = useState(1);
  const [isReleaseButtonDisabled, setIsReleaseButtonDisabled] = useState(true);
  const [isCheckboxChecked, setIsCheckboxChecked] = useState(false);
  const [userConfigFetched, setUserConfigFetched] = useState<any>(false);
  const [userPageSize, setUserPageSize] = useState<any>();
  const navigate = useNavigate();
  const [showWarningModal, setShowWarningModal] = useState(false);
  const [wipDataGlobal, setWipDataGlobal] = useState<any>({});
  const [WIPThresholdLimit, setWIPThresholdLimit] = useState(0);

  const isLoadingStates = [
    isLoading,
    isDBRSettingData,
    isUpdateUserConfig,
    isGetUserConfig,
    isDynamicReleaseExcelData,
    isGetFilterData,
    isGetUIConfigData,
  ];

  const {
    state: currFilter,
    setState: setCurrFilter,
    onFilterRemove,
    isFilterOpen,
    isMfgSelected,
    onAddFilter,
    onApplyFilter,
    toggleFilter,
    appliedFilters
  } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Prod_Dynamic_Release_Management);

  useEffect(() => {
    fetchDBRSettingsData();
  }, [])

  useEffect(() => {
    if (Object.entries(appliedFilters).length && userConfigFetched) {
      setCurrentPage(1);
      GetData(table1 ? 0 : 1);
    }
  }, [appliedFilters, userConfigFetched])
  
  const onDataUpdate = () => {
    setCurrentPage(1);
    setSelectedRows([]);
    setIsCheckboxChecked(false);
    setWipDataGlobal({});
    GetData(table1 ? 0 : 1, 1, 1);
  }

  useEffect(() => {
    if (table1 !== undefined) {
      setSelectedRows([]);
      setIsCheckboxChecked(false);
      getFilterData();
    }
  }, [table1])
  
  useEffect(() => {
    if (HeaderData.length > 0) {
      setColDef(getColumnDefinations(HeaderData, colDefCustomizations, extras))
      getUserColumnConfig();
    }

  }, [HeaderData])


  useEffect(() => {
    if (isSuccess) {
      notifySuccess("Fetched Data successfully!")
    }
    if (isError) {
      notifyError("Failed to load data!")
    }
  }, [isSuccess, isError])

  useEffect(() => {
    
    if (selectedRows.length) {
      setIsReleaseButtonDisabled(false);
    }
    else {
      setIsReleaseButtonDisabled(true);
    }

    handleWIPData();
    
  }, [selectedRows]);

  const handleWIPData = async () => {

    const cloneGraphData: InputData = _.cloneDeep(graphData);

    // Update cloneGraphData with existing WIP data
    selectedRows.forEach((rows:any) => {
      const existingWIPData = wipDataGlobal[rows.ok];
      if (existingWIPData) {
        Object.entries(existingWIPData).forEach(([key, value]:any) => {
          if (cloneGraphData[key]) {
            cloneGraphData[key]['Incremental WIP'] = (cloneGraphData[key]['Incremental WIP'] ?? 0) + value;
            cloneGraphData[key]['selected'] = true;
          }
        });
      }
    });

    const selectedOrdersWIP = await getWIPData(selectedRows.map((item: any) => item.ok));

    // Update cloneGraphData with newly fetched WIP data
    Object.values(selectedOrdersWIP).forEach((orderData:any) => {
      Object.entries(orderData).forEach(([key, value]:any) => {
        if (cloneGraphData[key]) {
          cloneGraphData[key]['Incremental WIP'] = (cloneGraphData[key]['Incremental WIP'] ?? 0) + value;
          cloneGraphData[key]['selected'] = true;
        }
      });
    });

    setFinalGraphData(convertData(cloneGraphData));
  };

  useEffect(() => {
    if (Object.entries(graphData).length) {
      // initially set selected true for all CCRS
      setFinalGraphData(convertData(graphData, true));
    }

  }, [graphData])

  useEffect(() => {
    setChartOptions({ ...chartoptions, data: finalGraphData })
  }, [finalGraphData])

  useEffect(() => {
    if (currentGridRef?.current && columnState?.length) {
      const result = currentGridRef.current.api.applyColumnState({
        state: columnState,
        applyOrder: true
      });
      if (!result) {
        console.error('Failed to apply column state 1');
      }
    }
  }, [columnState]);

  useEffect(() => {
    if (isReset) {
      handleSaveClick(masterUIConfig);
      setIsReset(false);
    }
  }, [isReset]);

  useEffect(() => {
    if (currentGridRef?.current) {
      setMasterUIConfig(currentGridRef?.current.api.getColumnState());
    }
  }, [colDef]);
  
  /**
  * Fetches UI configuration data and updates header state.
  * @async
  * @function setColumnDef
  * @description Makes an API call to get UI config data for a report,
  *           updates column definitions using `getColDef`,
  *           and sets header data using `setHeaderData`.
  * 
  * @calls getUIConfigData(reportName) - API call to fetch config.
  * @calls getColDef(response) - Method to set column definitions.
  * @state HeaderData - Updated with the fetched header data.
  */
  const setColumnDef = async () => {
    try {
      const response = await getUIConfigData(reportName);
      getColDef(response);
      setHeaderData(response.data.data);
    }
    catch (e) {
      console.log(e);
    }
  }

  /**
 * Handles the API response by checking its status and invoking appropriate callbacks.
 *
 * @param {ApiResponse} response - The response object returned from the API call.
 * @param {() => void} successCallback - Callback function to execute if the API response status is 200 (OK).
 * @param {string} errorMessage - Error message to display if the API response status is not 200 (OK).
 */
  const handleAPIResponse = (response: ApiResponse, successCallback: () => void, errorMessage: string) => {
    if (response?.status === 200) {
      successCallback();
    } else {
      notifyError(errorMessage);
    }
  };
 
  /**
   * 
   * @param [allOrders=0] - Flag indicating whether to include all orders.
   * @param [page=1] - The current page to be fetched for paginated data.
   * @param [graph=1] - Flag to determine if graph data should be fetched.
   * @param [isExcelExport=false] - Flag indicating if the data fetch is intended for Excel export.
   * @param [pageSize] - Optional page size for pagination; defaults to user's page size.
   * 
   */
  const GetData = async (allOrders = 0, page = 1, graph = 1, isExcelExport = false, pageSize?: any) => {
    const formattedFilters = formatFilterJSON(appliedFilters);

    const page_size = pageSize || userPageSize;
  
    try {
      if (isExcelExport) {
        const headersdata = currentGridRef?.current?.api.getColumnState();
        const body = getBodyForExcelExport({ headersdata, filterData: formattedFilters, colDefMap });
        const excelResponse = await getDynamicReleaseExcelData({
          isExcelExport: 1,
          body,
          graph: 0,
          ao: allOrders,
          report_name: FilterPageName.Prod_Dynamic_Release_Management,
        });
        handleAPIResponse(excelResponse, () => DownloadExcel(excelResponse, FilterPageName.Prod_Dynamic_Release_Management), "Failed to export to Excel");
      } else {
        const gridResponse = await getDynamicReleaseData({
          graph: 0,
          ao: allOrders,
          page,
          appliedFilters: formattedFilters,
          page_size,
        });
        handleAPIResponse(gridResponse, () => {

          if (!gridResponse?.data?.data || gridResponse?.data?.data?.length === 0) {
            setRowDataCount(0);
            setRowData([]);
            return;
          }

          setRowDataCount(gridResponse.data.data.count || 0);
          setRowData(gridResponse.data.data.results || []);
        }, "Failed to fetch Grid data!");
  
        if (graph) {
          const graphResponse = await getDynamicReleaseData({
            graph: 1,
            ao: allOrders,
            page,
            appliedFilters: formattedFilters,
            page_size,
          });
          setGraphData(graphResponse.data.data);
        }
      }
    } catch (error) {
      notifyError("An error has occurred");
      console.error(error);
    }
  };


  const getFilterData = async () => {
    try {
      const response = await getPageWiseFilterData({
        page_name: FilterPageName.Prod_Dynamic_Release_Management,
        ao: table1 ? 0 : 1
      });
      setFilterData(response?.data.data);
    } catch (error) {
      console.error(error);
    }
  }

  const onCloseWarningModal = () => {
    navigate("/landing-page");
  }
  
  const fetchDBRSettingsData = async () => {
    try {
      const DBRSettingsData = await getDBRsettingsData();
      const DBRSettings = DBRSettingsData?.data?.data || [];
      if (DBRSettings && DBRSettings.length) {
        const WIPThresholdLimit = DBRSettings.find((data: any) => data.flag === "WIPThresholdLimit") || 0;
        setWIPThresholdLimit(WIPThresholdLimit?.value);
        const isAutoRelease = DBRSettings.find((data: any) => data.flag === "AutoRelease")?.value === "1" || false;
        if (isAutoRelease) {
          setShowWarningModal(true);
        } else {
          setTable1(true);
          setColumnDef();
        }
      }

    } catch (e) {
      console.error(e);
    }
  }

  const colDefCustomizations = {
    Action: {
      floatingFilter: false,
      resizable: false,
      suppressMenu: true,
      cellRenderer: (params: any) => {
        if (!_.isEmpty(params.data)) {
          return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', color: backgroundColor, fontWeight: 'bold', fontFamily: 'roboto' }} onClick={() => { setRowRelease(true), setOrder_Key(params.data.ok), setMessage(`Release Order with id: ${params.data.oid} `), setShowReleaseModal(true) }}>
              <div >Release &nbsp; </div>
              <img height={14} width={14} src={userTheme ? '/assets/img/mto/dynamicReleaseManagement/arrow-icon-yellow.svg' : '/assets/img/mto/dynamicReleaseManagement/arrow-icon.svg'} alt='arrow-icon' />
            </div>
          )
        }
      }
    },
    BufferType: {
      cellRenderer: ColorCellRenderer
    },
    Route: {
      cellRenderer: (params: any) => {
        if (!_.isEmpty(params.data)) {
          return (
            <div style={{ display: "flex", alignItems: "center", gap: "1rem", width: "100%" }}>
              <div style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{params.value}</div>
              <img height={12} width={12} alt="edit icon" src={userTheme ? "/assets/img/mto/fullKitAssignment/edit_icon_yellow.svg" : "/assets/img/mto/fullKitAssignment/edit_icon.svg"} style={{ color: globalStyles.chooseThemeColor[themeUi]?.color4, cursor: "pointer" }}
                onClick={() => {
                if (params.data.rid === null) {
                  notifyError("No Route assigned to this order!");
                  return;
                }
                  setOrderDetails({ itemTypeId: params.data.itid, plantId: params.data.plid, routeNum: params.data.rid, orderKey: params.data.ok, pcqty: params.data.pcqty });
                setShowModal(true);
              }} />
            </div>
          )
        }
      }
    },
    OrderInFullKitToday: {
      cellRenderer: AvailabilityCellRenderer,
    },
    ColorPriority: {
      cellRenderer: ColorCellRenderer
    },
    BPP: {
      cellRenderer: BPPRenderer,
    },
    Tags: {
      cellRenderer: ColorCellRenderer,
      minWidth: 150
    },
    DropDown: {
      field: "",
      headerName: '',
      position: 0,
      resizable: false,
      headerCheckboxSelection: false,
      checkboxSelection: (params: any) => {
        // Only show on leaf rows, not group rows
        return params.node && !params.node.group;
      },
      maxWidth: 50,
      suppressMenu: true,
      floatingFilter: false,
    }
  }

  const extras: any = [

  ];

  const getWIPData = async (selectedOrders: any) => {
    try {
      // Exclude already fetched order IDs
      const newOrders = selectedOrders.filter(
        (ok: string) => !wipDataGlobal[ok]
      );

      
      if (newOrders.length === 0) {
        return {};
      }
  
      // Prepare the input for the API
      const filteredOrders = Object.keys(newOrders.reduce((acc: any, orderId: string) => {
        acc[orderId] = selectedOrders[orderId];
        return acc;
      }, {}));
  
      // Call the API with the filtered orders
      const response = await getDynamicReleaseData({
        graph: 0,
        ao: 0,
        page: 1,
        appliedFilters: formatFilterJSON(appliedFilters),
        wipObj: filteredOrders,
      });      
  
      if (response.status == 200) {
        // Update the global WIP data state
        setWipDataGlobal((prev: any) => ({
          ...prev,
          ...response?.data?.data,
        }));

        return response.data.data;
      }
    } catch (e) {
      console.log(e);
    }
    return {};
  };

  const updateGraphOnSelect = async () => {
    const selectedData = refGrid.current?.api.getSelectedRows();
    
    if (selectedData) {
      let mergedData: any = [...selectedRows]; // Start with the existing selected data

      //add newly selected rows in all selectedData
      selectedData.forEach((newItem: any) => {
        const index = mergedData.findIndex((item: any) => item.ok === newItem.ok);

        if (index !== -1) {
          // If the item exists, replace it
          mergedData[index] = newItem;
        } else {
          // Otherwise, add the new item
          mergedData.push(newItem);
        }
      });

      //remove unselected rows from all selectedData
      rowData.forEach((item: any) => {
        let isThere = 0;
        selectedData.forEach((selectedD: any) => {
          if (selectedD.ok === item.ok) {
            isThere = 1;
          }
        })

        if (isThere == 0) {
          mergedData = mergedData.filter((e: any) => e.ok !== item.ok)
        }
      })

      setSelectedRows(mergedData);
    }
    toggleCheckBox();
    refGrid.current.api.refreshCells();
  };

  const onFirstDataRendered =
    (params: any) => {
      const nodesToSelect: IRowNode[] = [];
      params.api.forEachNode((node: any) => {
        if (node.data && node.data.oid && existsInSelected(node.data.ok)) {
          node.data.ok = selectedRows[0].ok;
          nodesToSelect.push(node);
        }

      });
      params.api.setNodesSelected({ nodes: nodesToSelect, newValue: true });
      params.api.refreshCells();
      setCurrentGridRef(refGrid);
      toggleCheckBox();
      updateGraphOnSelect();

    }

  const options: GridOptions<any> = {
    getRowStyle: (params: any) => {
      return {
        background: params.node.rowIndex % 2 === 0 ? "#F4F4F4" : "#FFFFFF",
      };
    },
    rowHeight: 28,
    suppressRowClickSelection: true,
    suppressPaginationPanel: true,
    sideBar: {
      toolPanels: [
        {
          id: 'columns',
          labelDefault: 'Columns',
          labelKey: 'columns',
          iconKey: 'columns',
          toolPanel: 'agColumnsToolPanel',
          minWidth: 225,
          maxWidth: 225,
          width: 225
        },
      ],
    },

    columnDefs: colDef,
    defaultColDef: {
      resizable: true,
      suppressMenu: true,
      initialFlex: 1,
      autoHeaderHeight: true,
      floatingFilter: true,
      enableRowGroup: true,
      cellStyle: {
        "fontSize": "12px",
        'display': 'flex',
        'alignItems': 'center',

      },
    },
  };

  function convertData(input: InputData, selected = false): OutputData[] {
    const result: OutputData[] = [];
    // Convert the input object to an array of keys for iteration
    const keys = Object.keys(input);
    
    keys.forEach((key) => {
      const item = input[key];
      const releasedWIP = item?.wip ?? 0; 
      const incrementalWIP = item?.["Incremental WIP"] ?? 0;
      const actualLimit = (item?.limit ?? 0) * (1 + (WIPThresholdLimit / 100)) ; // considered threshold in limit
      
      const totalLoad = releasedWIP + incrementalWIP;
      let loadType = "Underloaded";
      if (actualLimit === totalLoad || actualLimit === 0) {
        loadType = "Balanced";
      } else if (actualLimit < totalLoad) {
        loadType = "Overloaded";
      }
      
      // Create the main data entry
      result.push({
        category: [loadType, item.ccr_name],
        "Released WIP": releasedWIP,
        Limit: actualLimit,
        // "Incremental WIP": index % 2 === 0 ? 20 : "", // Just as an example
        "Incremental WIP": incrementalWIP, // Just as an example
        selected: item.selected ?? selected,
        "CCR Name": item.ccr_name,
        "FOL Gap": item.fol_gap ?? 0,
      });
      
    });

    return result;
  }

  //phase 2
  // const Rectangle = useMemo(() => {
  //   return ({
  //     x,
  //     y,
  //     size,
  //     path,
  //   }: {
  //     x: number;
  //     y: number;
  //     size: number;
  //     path: any;
  //   }) => {
      
  //     const width = size * 4;
  //     const height = size / 6;

  //     path.clear();
  //     path.rect(x - width / 2, y - height / 2, width, height);
  //     path.closePath();
  //   };
  // }, []);

  function TooltipRenderer({ datum, xKey }: any) {
    return `
    <div style="background:#6C696A; style="transform: translateX(120px)" >
    <div  style=" color: white; padding: 10px 10px 4px;background-color: #6C696A; display: flex; justify-content: center; align-items: center; border-bottom: 1px dashed white">
        ${datum[xKey]}
    </div>
    <div style="color: white; background-color: #6C696A; padding: 10px;">
      <div style="display: flex; align-items: center;">
        <div style="margin-right: 10px; height: 3px; width: 15px; background-color: ${barColors["Released WIP"]}"></div>
        Released WIP:  ${datum["Released WIP"]}
      </div>
      <div style="display: flex; align-items: center;">
        <div style="margin-right: 10px; height: 3px; width: 15px; background-color: ${barColors["Incremental WIP"]}"></div>
        Incremental WIP:  ${datum["Incremental WIP"]}
      </div>
      <div style="display: flex; align-items: center;">
        <div style="margin-right: 10px; height: 3px; width: 15px; background-color: ${barColors["Limit"]}"></div>
        Limit:  ${datum["Limit"]}
      </div>
      
    </div>
    </div>`;
    // dont remove below code require for fol gap phase 2
    // <div style="display: flex; align-items: center;">
    //     FOL Gap:  ${datum["FOL Gap"]}
    //   </div>
  }

  const barColors = {
    "Released WIP": "#191919",
    "Incremental WIP": "#4BAAF7",
    "Limit": "#E53F3F",
  }

  const [chartoptions, setChartOptions] = useState<any>({
    // data: graphData,
    series: [
      {
        type: 'bar',
        xKey: 'category',
        yKey: "Released WIP",
        stacked: true,
        strokeWidth: 0,
        visible: true,
        fill: barColors["Released WIP"],
        itemStyler: ({ datum }:any) => {
          return {
            fillOpacity: datum.selected == true ? 1 : 0.5,
          };
        },
        tooltip: {
          position: { placement: "right" },  // anchor to bar
          renderer: TooltipRenderer
        },
      },
      {
        type: 'bar',
        xKey: 'category',
        yKey: "Incremental WIP",
        stacked: true,
        strokeWidth: 0,
        visible: true,
        fill: barColors["Incremental WIP"],
        tooltip: {
          position: { placement: "right" },  // anchor to bar
          renderer: TooltipRenderer
        }
      },
      {
        type: "scatter",
        xKey: "category",
        yKey: "Limit",
        // shape: Rectangle,
        size: 5,
        strokeWidth: 0,
        visible: true,
        fill: barColors["Limit"],
        tooltip: {
          position: { placement: "right" },  // anchor to bar
          renderer: TooltipRenderer
        },
      }
    ],
    axes: [
      {
        type: "grouped-category",
        position: "bottom",
        // paddingInner: 0.5,       // Gap between categories
        // paddingOuter: 0.2,       // Gap before first and after last category
        // groupPaddingInner: 0.6,  // Gap between bars in the same category group
        gridLine: {
          enabled: false
        },
        depthOptions: [
          {
            label: {
              fontSize: 10,
              rotation: -20,
              avoidCollisions: true,
              wrapping: "hyphenate",
            }
          },
          {
            tick: { enabled: true, stroke: 'black' },
            label: { fontWeight: "bold", avoidCollisions: true }
          },
        ],
      },
      {
        type: "number",
        position: "left",
        title: {
          text: "Days"
        },
        gridLine: {
          enabled: false
        },
      },
    ],
    legend: {
      enabled: false,
    },
  })

  const onOrderRelease = () => {
    setRowRelease(false);
    setOrder_Key('');
    setMessage(`Release ${selectedRows.length} selected orders out of ${rowDataCount}`)
    setShowReleaseModal(true);
  }

  const handlePageChangeCumulative = async (pageNumber: number) => {
    setCurrentPage(pageNumber);
    if (table1) {
      GetData(0, pageNumber, 0);
    }
    else {
      GetData(1, pageNumber, 0);
    }
  };

  const savePageSize = (pageSize: any) => {
    if (pageSize) {
      setCurrentPage(1)
      setUserPageSize(pageSize);
      handleSaveClick(undefined, pageSize);
      GetData(table1 ? 0 : 1, 1, 0, false, pageSize);
    } else {
      notifyError("Invalide page size");
    }
    
  }

  const onCheckBoxToggle = (e: any) => {
    const isChecked = e.target.checked;
    setIsCheckboxChecked(isChecked);

    if (isChecked) {
      refGrid.current.api.selectAll();
    } else {
      refGrid.current.api.deselectAll();
    }
  }

  const toggleCheckBox = () => {
    
    const selectedNodes = refGrid?.current?.api?.getSelectedRows();
    const totalRows = refGrid?.current?.api?.getDisplayedRowCount()

    setIsCheckboxChecked(selectedNodes?.length > 0 && selectedNodes?.length === totalRows);
  };


  const existsInSelected = (ok: string): boolean => {
    for (let index = 0; index < selectedRows.length; index++) {
      const element: any = selectedRows[index];
      if (element.ok === ok) {
        return true;
      }

    }
    return false;
  }
  
    
  const getUserColumnConfig = async () => {
    try {
      const data = await getUserUIReportConfigData({
        un: user.user.name,
        rn_id: UIGridCode.ProdDynamicReleaseManagement
      });

      setUserConfigFetched(true)
      const newConfig = data?.data?.data[0] ? JSON.parse(data?.data?.data[0]?.columns_settings) || [] : [];
      setUserPageSize(newConfig.pageSize ? Number(newConfig.pageSize) : undefined);
      setColumnState(newConfig.cs);
  
      if (!data) {
        console.error('Failed to apply column state');
      }
    } catch (error) {
      console.error(error);
    }
  }
      
  
  const handleSaveClick = async (coldefs?: any, page_size?: any) => {
    try {
      if (coldefs) {
        const fullConfig = { cs: coldefs, pageSize: userPageSize };
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.ProdDynamicReleaseManagement,
          cs: JSON.stringify(fullConfig),
        };
        await updateUserUIReportConfigData([payload]);
        setColumnState([...coldefs]);
        
      }
      else if (page_size) {
        const config = columnState;
        const fullConfig = { cs: config, pageSize: page_size };
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.ProdDynamicReleaseManagement,
          cs: JSON.stringify(fullConfig),
        };
        await updateUserUIReportConfigData([payload]);
      }
      else {
        if (currentGridRef?.current?.api) {
          const config = currentGridRef.current.api.getColumnState();

          const fullConfig = { cs: config, pageSize: userPageSize };


          const payload = {
            un: user.user.name,
            rn_id: UIGridCode.ProdDynamicReleaseManagement,
            cs: JSON.stringify(fullConfig)
          }
          await updateUserUIReportConfigData([payload]);
          await getUserColumnConfig();
        }
      }

    } catch (error) {
      console.error(error);
    }
  }

  const handleResetClick = () => {
    setIsReset(true);
  }
  
  const ExcelData = () => {
    GetData(table1 ? 0 : 1, 0, 0, true)
  }

  const ReleaseOrderHeader: any = (
    <>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', fontSize: '18px', fontWeight: 'bold', gap: '15px' }}>

        <div style={{ borderRadius: '5px', background: 'white', padding: '10px 30px', display: 'flex', justifyContent: 'center', alignItems: 'center', boxShadow: 'rgba(133, 132, 132, 0.247) -5px 4px 10px', gap: '10px' }}>
          <InputCheckBox checked={isCheckboxChecked} onChange={onCheckBoxToggle} type="checkbox" theme={themeUi} />
          <p>Release</p>
        </div>
        <VFButton
          data-testid={"isReleaseBtn"}
          onClick={() => onOrderRelease()}
          themeUi={themeUi}
          disabled={false}
          style={{
            cursor: isReleaseButtonDisabled ? "not-allowed" : "pointer",
            height: "50px",
            width: "60px",
            borderRadius: "3px",
            opacity: isReleaseButtonDisabled ? 0.5 : 1, // Visual cue for disabled
            pointerEvents: isReleaseButtonDisabled ? "none" : "auto", // Prevent click when disabled
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

  return (
    <>
      <Wrapper>
        {
          isApiLoading(...isLoadingStates) && <OverlayLoader />
        }
        <MTOActionToolBar
          comp="FullKitAssignment"
          isExcelExport
          onExcelExportClick={ExcelData}
          isAddFilterButton
          themeUi={themeUi}
          handleSaveClick={handleSaveClick}
          handleResetClick={handleResetClick}
          isFilterOpen={isFilterOpen}
          onAddFilter={onAddFilter}
          toggleFilter={toggleFilter}
          onApplyFilter={onApplyFilter}
          multiFilter={currFilter}
          setMultiFilter={setCurrFilter}
          onFilterRemove={onFilterRemove}
          isMfgSelected={isMfgSelected}
          ReleaseOrderHeader={ReleaseOrderHeader}
        />
        <VFWarningModal
          warningMsg={"Access to this page is restricted because orders will be automatically released in the current system."}
          actionButtonText={"Ok"}
          showWarningModal={showWarningModal}
          onCloseWarningModal={onCloseWarningModal}
          themeUI={user.user.theme_ui}
        />

        <SCTabHeader style={{ marginTop: '5px' }}>

          <BPRViewTableHeaderTab onClick={() => { setTable1(true) }} status={table1} marLeft={true} themeUi={themeUi} zIndex={2} style={{ width: '250px', fontSize: '12px' }} >
            Orders with simulated full kit
          </BPRViewTableHeaderTab>
          <BPRViewTableHeaderTab onClick={() => { setTable1(false) }} status={!table1} marLeft={true} themeUi={themeUi} zIndex={1} style={{ width: '250px', fontSize: '12px' }} >
            All Orders
          </BPRViewTableHeaderTab>
        </SCTabHeader>
        <VFTable
          ref={refGrid}
          rowData={rowData}
          disableZoomScaling
          gridOptions={options}
          columnDefs={options.columnDefs}
          onFilterChanged={() => { Object.keys((currentGridRef?.current?.api?.getFilterModel()))?.length > 0 ? setIsDisabled(false) : setIsDisabled(true) }}
          rowSelection="multiple"
          onSelectionChanged={updateGraphOnSelect}
          onRowDataUpdated={onFirstDataRendered}
          maintainColumnOrder={true}
        />
        <div style={{ width: '100%' }}>

          <VFPagination
            selectedRows={0}
            rowsPerPage={userPageSize || pagination.mtoPageSize}
            totalRows={rowDataCount}
            currentPage={currentPage}
            handleChangePage={handlePageChangeCumulative}
            showPagination
            resetGridRef={currentGridRef}
            isDisabled={isDisabled}
            customPageSizeEnabled={true}
            savePageSize={savePageSize}
            userPageSize={userPageSize}
          />
        </div>
        <Button arrowName={!hide ? "bg_arrow_down" : "bg_arrow_up"} themeUi={themeUi} onClick={() => { setHide(!hide) }}> {hide ? "Show" : "Hide"} Load Chart</Button>
         <div className='chart-wrapper' style={{ flex: !hide ? 1:0, overflow: hide ? "hidden":"unset", minHeight: 0, marginBottom: hide ? "0" : "10px", boxShadow: "0px 6px 12px #81818129"}}>
            <CustomLegend chartOptions={chartoptions} setChartOptions={ setChartOptions } />
            <div className='chart-scroll' style={{overflowX:chartoptions?.data?.length > 15 ? "scroll" : "hidden"}}>
              <AgCharts ref={graph} style={{ height: "100%", width: chartoptions?.data?.length > 15 ? `${100*chartoptions?.data?.length + "px"}` : "100%" }} options={chartoptions} /> 
            </div>
        </div>
        {showModal && <EditRouteModal orderDetails={orderDetails} chartoptions={chartoptions} setChartOptions={setChartOptions} onDataUpdateCallback={onDataUpdate} showModal={showModal} setShowModal={setShowModal} themeUi={themeUi} />}
        
        {showReleaseModal && <ReleaseModal onDataUpdateCallback={onDataUpdate} setResetReleaseCheckbox={setIsCheckboxChecked} rowRelase={rowRelease} message={message} themeUi={themeUi} totalOrders={120} order_key={order_key} selectedOrders={selectedRows} showModal={showReleaseModal} setShowModal={setShowReleaseModal} />}
      </Wrapper>
    </>
  )
}

export default DynamicReleaseManagement