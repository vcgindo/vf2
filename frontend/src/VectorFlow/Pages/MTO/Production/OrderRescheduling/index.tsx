import { useState, useEffect, useRef } from "react";
import VFFloatingTab from "../../../../../components/VectorFLOW/commons/VFFloatingTab";
import MTOActionToolBar from "../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar";
import {
  ApplyZoomOut,
  OrderReschedulingWrapper,
  VFTableWrapper,
} from "./styles";
import VFTable from "../../Common/VFTable";
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton";
import DueDateCellRenderer from "./DueDateCellRenderer";
import {
  usePutUpdateOrderDueDate,
  useGetOrderSchedulingPageData,
  useGetOrderSchedulingExcelData,
} from "../../../../Services/MTO/Production/OrderRescheduling";
import { AgGridReactProps } from "ag-grid-react";
import { GridRef } from "../../../../types/MDM";
import { notifySuccess, notifyError } from "../../../../../helpers/notify";
import { toast } from "react-toastify";
import { IRowNode } from "ag-grid-enterprise";
import OverlayLoader from "../../Common/Loader";
import { useGetUIConfigData } from "../../../../../VectorFlow/Services/MTO/Common/UIConfig";
import {
  DownloadExcel,
  formatFilterJSON,
  getBodyForExcelExport,
  getColumnDefinations,
} from "../../../../../helpers/utils";
import VFPagination from "../../Common/VFPagination";
import { pagination, UIGridCode, FilterPageName } from "../../Common/Enum";
import {
  useGetUserUIConfigData,
  useUpdateUserUIConfigData,
} from "../../../../../VectorFlow/Services/MTO/Common/UserUIConfig";
import { useUserData } from "../../../../../context/index";
import useColDef from "../../../../../hooks/useColDef";
import useFilter from "../../../../../hooks/useFilter";
import { useGetFilterData } from "../../../../../VectorFlow/Services/MTO/Common/CommonFilter";
import _ from "lodash";


interface RowDataType {
  odk: string;
  dd?: string;
  [key: string]: any; // Add this line to allow for additional properties
}
const APIFilterConfig = {
  filSecVisConfig: {
    Prod_Order_Rescheduling: {
      mjr: false,
      or: true,
      res: true,
      cus: true
    },
  }
};

const OrderRescheduling = () => {
  const { mutateAsync: putUpdateOrderDueDate } = usePutUpdateOrderDueDate();
  const { mutateAsync: getOrderSchedulingPageData } =
    useGetOrderSchedulingPageData();
  const {
    mutateAsync: updateUserUIReportConfigData,
    isLoading: isUpdateUserConfig,
  } = useUpdateUserUIConfigData();
  const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } =
    useGetUserUIConfigData();

  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const refGraph1 = useRef<GridRef>(null);
  const [selectedRowData, setSelectedRowData] = useState<RowDataType[]>([]);
  const [currentGridRef, setCurrentGridRef] = useState<any>(null);
  const [columnState, setColumnState] = useState<any>([]);
  const [isReset, setIsReset] = useState<any>(undefined);
  const [colDef, setColDef] = useState([{}]);
  const [HeaderData, setHeaderData] = useState([]);
  const { mutateAsync: getUIConfigData } = useGetUIConfigData();
  const { user } = useUserData();
  const [rowData, setRowData] = useState<RowDataType[]>([]);
  const [currData, setCurrData] = useState<any>(null);
  const { mutateAsync: getOrderReschedulingExcelData } =
    useGetOrderSchedulingExcelData();
  const { getColDef, colDefMap } = useColDef();
  const [masterUIConfig, setMasterUIConfig] = useState([]);

  const [isDisabled, setIsDisabled]= useState<boolean>(true)
  
  const [ userPageSize, setUserPageSize] = useState<any>();
  const [userConfigFetched, setUserConfigFetched] = useState<any>(false);

  const [filterData, setFilterData] = useState({});

  const { mutateAsync: getPageWiseFilterData, /*isLoading*/ } = useGetFilterData()

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
  } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Prod_Order_Rescheduling);

  const themeUi = user?.user?.theme_ui;

  const GetData = async (isExcelExport = false, page?: number, page_size?: number) => {  
    setIsLoading(true); 
    if (isExcelExport) {
      const headersdata = refGraph1?.current?.api?.getColumnState();
      const formatedFilters = formatFilterJSON(appliedFilters);
      const body = getBodyForExcelExport({ headersdata, filterData : formatedFilters, colDefMap });
      try {
        const response = await getOrderReschedulingExcelData({
          body,
          isExcelExport: 1,
          report_name: FilterPageName.Prod_Order_Rescheduling,
        });
        DownloadExcel(response, FilterPageName.Prod_Order_Rescheduling);
      } catch (e) {
        console.log(e);
      }
    } else {
      try {
        const formatedFilters = formatFilterJSON(appliedFilters);
        const APIData = await getOrderSchedulingPageData({pageNum:page, pageSize: page_size || userPageSize || pagination.mtoPageSize,appliedFilters: formatedFilters});
        setCurrData(APIData);
        const newRowData = [...APIData.data.data.results];
        if (newRowData.length === 0) {
          refGraph1.current?.api.showNoRowsOverlay(); 
          setRowData(newRowData)
        } else {
          refGraph1.current?.api.hideOverlay(); 
          newRowData.forEach((el) => {
            el.oldDate = el.dd;
          });
          setRowData(newRowData);
        }
      } catch (e) {
        notifyError("Failed to fetch Grid data!");
      }
    }
    setIsLoading(false);
  };


  const getSelectedRowData = () => {
    const selectedData = refGraph1.current?.api.getSelectedRows();

    //  logic to get the unselected row and set the default date to it
    // const newRowData:any= _.cloneDeep([...rowData]);
    // newRowData.forEach((ele:any)=>{
    //   if(!selectedData?.find((el:any)=>{ele.odk===el.odk})){
    //     newRowData.dd = newRowData.oldDate; 
    //   }
    // })
    
    if (selectedData) {
      let mergedData = [...selectedRowData]; // Start with the existing selected data

      selectedData.forEach((newItem) => {
        const index = mergedData.findIndex((item) => item.odk === newItem.odk);
        if (index !== -1) {
          // If the item exists, replace it
          mergedData[index] = newItem;
        } else {
          // Otherwise, add the new item
          mergedData.push(newItem);
        }
      });

      rowData.forEach((item) => {
        let isThere = 0;
        selectedData.forEach((selectedD) => {
          if (selectedD.odk === item.odk) {
            isThere = 1;
          }
        });

        if (isThere === 0) {
          mergedData = mergedData.filter((e) => e.odk !== item.odk);
          
        }
      });
      setSelectedRowData(mergedData);
    }
  };

  const agGridProps: AgGridReactProps = {
    suppressRowTransform: true,
    tooltipShowDelay: 0.3,
    tooltipTrigger: "focus",
    tooltipInteraction: true,
    readOnlyEdit: false,
    pagination: true,
    suppressRowClickSelection: true,
    // rowHeight: 40,
    defaultColDef: {
      floatingFilter: true,
      resizable: true,
      cellDataType: false,
      // minWidth: 140,
      wrapHeaderText: true,
      autoHeaderHeight: true,
      cellStyle: {
        "textAlign": "center",
        "textOverflow": "ellipsis",
      },
      flex: 1,
    },
    onSelectionChanged: getSelectedRowData,
    enableFillHandle: true,
  };

  const [currTab, setCurrTab] = useState("Unschedule");
  const tabs = [
    { label: "Unschedule", value: "Unschedule", id: "Unschedule" },
    {
      label: "Overwrite Due Date",
      value: "Overwrite Due Date",
      id: "Overwrite Due Date",
    },
  ];

  
  const reportName = "OrderRescheduling";

  const setColumnDef = async () => {
    try {
      const response = await getUIConfigData(reportName);
      getColDef(response);
      setHeaderData(response.data.data);
    } catch (e) {
      console.log(e);
    }
  };

  useEffect(() => {
    setColumnDef();
  }, []);

  const extras = [
    {
      field: "",
      colId: "",
      resizable: false,
      position: 0,
      headerCheckboxSelection: (params:any) => {
        // Only show if no grouping is applied
        return params.api.getRowGroupColumns().length === 0;
      },
      checkboxSelection: (params:any) => {
        // Only show on leaf rows, not group rows
        return params.node && !params.node.group;
      },
      minWidth: 50,
      maxWidth: 50,
      flex: 1,
      initialHide: false,
      pinned: "left",
      suppressMenu: true,
      floatingFilter: false,
      filterParams: {
        buttons: ['reset'], // Adds Apply and Clear buttons
      },
    },
  ];


  const customHeader = {
    DueDate: {
      autoHeaderHeight: true,
      wrapHeaderText: true,
      cellRenderer: currTab === "Unschedule" ? "" : DueDateCellRenderer,
      flex: 1,
      // initialWidth: 200,
      // width: 200,
      filter: "agMultiColumnFilter",
      floatingFilter: true,
    },
    Reason: {
      colId: "rs",
      field: "rs",
      headerName: "Reason",
      hide: false,
      cellRenderer: (params: any) => {
        if (!params.node.isSelected() && !_.isEmpty(params.data)) {
          params.data.rs = "";
        } else if (!_.isEmpty(params.data)) {
          return params.data.rs;
        }
        return "";
      },
      autoHeaderHeight: true,
      wrapHeaderText: true,
      flex: 1,
      cellStyle: (params : any)=> {
        if(params.node.isSelected()){
        return {
          backgroundColor: 'white',
          border: '1px solid #b9bdba',
          color: 'black',
          padding: '1px',
        }
      }else{
        return {
          backgroundColor: 'white',
        }
      }
    },
      filter: "agMultiColumnFilter",
      editable: (params: any) => params.node.isSelected(),
      floatingFilter: true,
    },
  };

  useEffect(() => {
     getFilterData();
    
  },[])     


  useEffect(() => {
    if (HeaderData.length > 0) {
      const headerDataCopy = JSON.parse(JSON.stringify(HeaderData));
      setColDef(getColumnDefinations(headerDataCopy, customHeader, extras));
      getUserColumnConfig();
    }
  }, [HeaderData]);

  useEffect(() => {
    if(currTab && userConfigFetched) {
      const headerDataCopy = JSON.parse(JSON.stringify(HeaderData));
      setColDef(getColumnDefinations(headerDataCopy, customHeader, extras));
      GetData(false, 1);
      if(refGraph1){
        refGraph1.current?.api.deselectAll();
      }
    }
  }, [currTab]);

  const handlePageChangeCumulative = async (pageNumber: number) => {
    setCurrentPage(pageNumber);
    GetData(false,pageNumber);
  };

  type OutputItem = {
    ok: string;
    r: string;
    dd?: string;
  };

  type Output = {
    unm: string;
    isUnSch: number;
    ordData: OutputItem[];
  };

  function convertJsonForUnschedule(
    inputArray: any,
    username: string,
    isUnSch: number
  ): Output {
    const output: Output = {
      unm: username,
      isUnSch: isUnSch,
      ordData: [],
    };


    inputArray.forEach((item: any) => {
      const ordDataItem: OutputItem = {
        ok: item.odk || "",
        r: item.rs || "",
      };
      output.ordData.push(ordDataItem);
    });

    return output;
  }

  function convertJsonForDueDate(
    inputArray: any,
    username: string,
    isUnSch: number
  ): Output| boolean {
    const output: Output = {
      unm: username,
      isUnSch: isUnSch,
      ordData: [],

    };


    let validData:any = true;
    inputArray.forEach((item: any) => {
      if(item.dd===item.oldDate){
        notifyError("Make sure you change the date before overwriting!")
        validData = false;
      }
      const ordDataItem: OutputItem = {
        ok: item.odk || "",
        dd: item.dd || "",
        r: item.rs || "",
      };
      output.ordData.push(ordDataItem);
    });

    if(validData === false)return validData;
    return output;
  }

  const reasonCheck = (data: any): boolean => {
    for (let index = 0; index < data.length; index++) {
      const element = data[index];
      if (element.r.toString().length === 0) {
        return false;
      }
    }
    return true;
  };

  const savePageSize = (pageSize: any) => {
    if (pageSize) {
        setCurrentPage(1)
        setUserPageSize(pageSize);
        handleSaveClick(undefined, pageSize);
        GetData(false,1,pageSize);
    } else {
        notifyError("Invalide page size");
    }
  }   

    useEffect (() => {
      if(Object.entries(appliedFilters).length && userConfigFetched){
        GetData(false,1);
      }
    }, [appliedFilters,userConfigFetched])
  


  const PostData = async (data: any, message: string): Promise<boolean> => {
    if (reasonCheck(data.ordData)) {
      try {
        const response = await putUpdateOrderDueDate(
          JSON.parse(JSON.stringify(data))
        );

        if (response.status === 200) {
          if (refGraph1) {
            refGraph1.current?.api.deselectAll();
          }
          toast.dismiss();
          notifySuccess(message);
        } else {
          toast.dismiss();
          notifyError("Failed to update data");

          return false;
        }
      } catch (error) {
        toast.dismiss();
        notifyError("Failed to update Data!");
        return false;
      }
    } else {
      toast.dismiss();
      notifyError("Make sure you provide a reason for every update !");
      // if (refGraph1) {
      //     refGraph1.current?.api.deselectAll();
      // }
      return false;
    }
    return true;
  };

  const unschedule = async () => {
    setIsLoading(true);
    try {
      const finalData = convertJsonForUnschedule(selectedRowData, user.user.name, 1);
      const isSuccesss = await PostData(
        finalData,
        "Order Unscheduled Successfully !"
      );
      if (isSuccesss) {
        setSelectedRowData([]);
        await handlePageChangeCumulative(currentPage);
      }
    } catch (error) {
      notifyError("Failed to unschedule order!");
    } finally {
      setIsLoading(false);
    }
  };

  const overwriteDD = async () => {
    setIsLoading(true);
    try {
      const finalData = convertJsonForDueDate(
        selectedRowData,
        user.user.name,
        0
      );

      if(finalData===false){
        setIsLoading(false);
        return;
      }
      const isSuccess = await PostData(
        finalData,
        "Order Due date updated successfully !"
      );
      if (isSuccess) {
        setSelectedRowData([]);
        await handlePageChangeCumulative(currentPage); // Refresh the grid data
      }
    } catch (error) {
      notifyError("Failed to update Due Date!");
    } finally {
      setIsLoading(false);
    }
  };

  const existsInSelected = (reqOdk: string): boolean => {
    for (let index = 0; index < selectedRowData.length; index++) {
      const element = selectedRowData[index];
      if (element.odk === reqOdk) {
        return true;
      }
    }
    return false;
  };

  const onFirstDataRendered = (params: any) => {
    const nodesToSelect: IRowNode[] = [];
  
    params.api.forEachNode((node: any) => {
      if (node.data && node.data.odk && existsInSelected(node.data.odk)) {
        node.data.rs = selectedRowData[0].r;
        for (let index = 0; index < selectedRowData.length; index++) {
          const element = selectedRowData[index];
          if (element.odk === node.data.odk) {
            node.data.rs = element.rs;
            node.data.dd = element.dd;
            node.data.oldDate = element.oldDate;
          }
        }
        nodesToSelect.push(node);
        
      }
    });
  
   
    params.api.setNodesSelected({ nodes: nodesToSelect, newValue: true });
    params.api.sizeColumnsToFit();
    setCurrentGridRef(refGraph1);
  };
  

  const getUserColumnConfig = async () => {
    try {
      const data = await getUserUIReportConfigData({
        un: user.user.name,
        rn_id: UIGridCode.ProdOrderRescheduling,
      });

      const newConfig = data?.data?.data?.length ? JSON.parse(data?.data?.data?.[0]?.columns_settings) || [] : [];
      setUserPageSize(newConfig.pageSize ? Number(newConfig.pageSize) : undefined);
      setColumnState(newConfig.cs);
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
        const fullConfig = {cs: coldefs, pageSize:userPageSize };
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.ProdOrderRescheduling,
          cs: JSON.stringify(fullConfig),
        };
        await updateUserUIReportConfigData([payload]);
        setColumnState([...coldefs]);

      } else if(page_size){
        const fullConfig = {cs: columnState, pageSize:page_size };
        const payload = {
          un: user.user.name,
          rn_id: UIGridCode.ProdOrderRescheduling,
          cs: JSON.stringify(fullConfig),
        };
        await updateUserUIReportConfigData([payload]);
      }
      
      else {
        if (currentGridRef?.current?.api) {
          const config = currentGridRef.current.api.getColumnState();
          const fullConfig = { cs: config, pageSize:userPageSize };

          const payload = {
            un: user.user.name,
            rn_id: UIGridCode.ProdOrderRescheduling,
            cs: JSON.stringify(fullConfig),
          };

          await updateUserUIReportConfigData([payload]);
          await getUserColumnConfig();
        }
      }
    } catch (error) {
      console.error(error);
    }
  };

  const handleResetClick = () => {
    setIsReset(true);
  };

  const getFilterData = async () => {
    try {
        const response = await getPageWiseFilterData({page_name: FilterPageName.Prod_Order_Rescheduling });
        setFilterData(response?.data.data);
    } catch (error) {
        console.error(error);
    }
  }

  // const resetGridFilters = () =>{
  //   currentGridRef.current.api.setFilterModel(null)
  // }
  useEffect(() => {
    if (currentGridRef?.current && columnState?.length) {
      const result = currentGridRef?.current?.api.applyColumnState({
        state: columnState,
        applyOrder: true,
      });
      if (!result) {
        console.error("Failed to apply column state 1", result);
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
    if (currentGridRef?.current && !masterUIConfig.length) {
      setMasterUIConfig(currentGridRef?.current.api.getColumnState());
    }
  }, [colDef]);


  const GetExcelData = async () => {
    GetData(true);
  };

  return (
    <>
      <OrderReschedulingWrapper
        style={{
          width: "100%",
          position: "relative",
          height: "100%",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <MTOActionToolBar
          comp={"orderReschedule"}
          themeUi={themeUi}
          isExcelExport
          onExcelExportClick={GetExcelData}
          handleSaveClick={handleSaveClick}
          handleResetClick={handleResetClick}

          isAddFilterButton
          isFilterOpen={isFilterOpen}
          onAddFilter={onAddFilter}
          toggleFilter={toggleFilter}
          onApplyFilter={onApplyFilter}
          multiFilter={currFilter}
          setMultiFilter={setCurrFilter}
          onFilterRemove={onFilterRemove}
          isMfgSelected={isMfgSelected}



        />
        {(isLoading || isUpdateUserConfig || isGetUserConfig) && (
          <OverlayLoader />
        )}

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            flex: 1,
          }}
        >
          <div style={{ margin: "10px 0" }}>
            <ApplyZoomOut>
              <VFFloatingTab
                handleClick={(e) => setCurrTab(e.value)}
                tabs={tabs}
                defaultTab={0}
              />
            </ApplyZoomOut>
          </div>
          <div style={{ width: "100%", height: "100%" }}>
            <VFTableWrapper>
              <VFTable
                {...agGridProps}
                disableZoomScaling
                columnDefs={colDef}
                rowData={rowData}
                ref={refGraph1}
                enableRangeSelection={true}
                rowSelection="multiple"
                onFilterChanged={()=>{Object.keys((currentGridRef?.current?.api?.getFilterModel()))?.length>0 ? setIsDisabled(false) : setIsDisabled(true)}}
            
                onFirstDataRendered={onFirstDataRendered}
                onGridReady={onFirstDataRendered}
                onRowDataUpdated={onFirstDataRendered}
                pagination={false}
                height={"100%"}
                maintainColumnOrder={true}
              />
              <VFPagination
                selectedRows={0}
                rowsPerPage={userPageSize || pagination.mtoPageSize}
                totalRows={currData ? currData?.data?.data?.count : 0}
                currentPage={currentPage}
                handleChangePage={(page)=>{handlePageChangeCumulative(page)}}
                resetGridRef={currentGridRef}
                isDisabled={isDisabled}
                customPageSizeEnabled = {true}
                savePageSize={savePageSize}
                userPageSize={userPageSize}

              />

              <div style={{ width: "100%" }}>
                <div
                  style={{
                    width: "100%",
                    height: "65px",
                    padding: "20px 0",
                    display: "flex",
                    justifyContent: "left",
                    alignItems: "center",
                  }}
                >
                  <ApplyZoomOut>
                    {currTab === "Unschedule" ? (
                      <VFButton
                        disabled={
                          selectedRowData && selectedRowData[0] ? false : true
                        }
                        style={{ width: "150px" }}
                        themeUi={themeUi}
                        onClick={unschedule}
                      >
                        Unschedule
                      </VFButton>
                    ) : (
                      <VFButton
                        disabled={
                          selectedRowData && selectedRowData[0] ? false : true
                        }
                        style={{ width: "200px" }}
                        themeUi={themeUi}
                        onClick={overwriteDD}
                      >
                        Overwrite Due Date
                      </VFButton>
                    )}
                  </ApplyZoomOut>
                </div>
              </div>
            </VFTableWrapper>
          </div>
        </div>
      </OrderReschedulingWrapper>
    </>
  );
};

export default OrderRescheduling;
