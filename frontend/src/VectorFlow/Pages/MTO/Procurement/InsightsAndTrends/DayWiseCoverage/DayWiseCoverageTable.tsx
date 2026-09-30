import { GridOptions } from "ag-grid-enterprise";
import { useEffect, useRef, useState } from "react";
import VFTable from "../../../Common/VFTable";
import CustomGroupCellRenderer from "./CustomGroupCellRenderer";
import DayWiseCoverageDetailsCellRenderer from "./DayWiseCoverageDetailsCellRenderer";
import { useGetDayWiseCoverageData } from "../../../../../../VectorFlow/Services/MTO/Procurement/DayWiseCoverage";
import { GridFilterWrapper, TextBtn } from "../../../Common/VFPagination/styles";
import { useUserData } from "../../../../../../context";

interface IDayWiseCoverageProps {
  columnState: any,
  setCurrentGridRef: any,
  colDef: any,
  currentGridRef: any,
  selectedDate: string,
  startDate: string,
  endDate: string,
  setLoading: any
}

const DayWiseCoverageTable = ({
  columnState,
  setCurrentGridRef,
  colDef,
  currentGridRef,
  selectedDate,
  startDate,
  endDate,
  setLoading,
}: IDayWiseCoverageProps) => {

  // const extra = [
  //   {
  //       headerName: "Action",
  //       cellRenderer: () => <div>Hello</div>,
  //       position: 0
  //   }
  // ]
  const gridRef = useRef<any>(null);
  const [rowData, setRowData] = useState([]);
  const { mutateAsync: getData, isLoading: isGridLoading } = useGetDayWiseCoverageData();
  const [isDisabled, setIsDisabled]= useState<boolean>(true)
  const { user } = useUserData();
  const theme_ui = user.user.theme_ui

  const getGridData = async () => {
    if (selectedDate) {
      const data = await getData({ startDate: startDate, endDate: endDate, plannedReleaseDate: selectedDate });
      setRowData(data?.data?.data)
    }
  }

  
  const clearGridFilter = () =>{
    gridRef?.current?.api.setFilterModel(null);
      setIsDisabled(true);
}

  const CustomStatusPanel = () => {
          return (
              <GridFilterWrapper style={{marginTop:'15px'}}>
                  <TextBtn onClick={clearGridFilter} disabled={isDisabled} themeUi={theme_ui}>
                      Clear All Grid Filters
                  </TextBtn>  
              </GridFilterWrapper>           
          );
      };
      

  useEffect(() => {
    getGridData()
  }, [selectedDate])

  useEffect(() => {
    setLoading(isGridLoading)
  }, [isGridLoading])

  const options: GridOptions<any> = {
    getRowStyle: (params: any) => {
      return {
        background: params.node.rowIndex % 2 === 0 ? "#EBEBEB" : "#F7F7F7",
      };
    },
    columnDefs: colDef,
    defaultColDef: {
      filter: "agTextColumnFilter",
      floatingFilter: true,
      resizable: true,
      cellStyle: {
        display: "flex",
      }
    },
    autoGroupColumnDef: {
      headerName: "Group",
      cellRenderer: CustomGroupCellRenderer,
      suppressMenu: true,
      initialWidth: 260,
    },
    masterDetail: true,
    detailCellRendererParams: {
      innerHeight: 400,
    },
    detailCellRenderer: DayWiseCoverageDetailsCellRenderer,
    detailRowAutoHeight: true,
    sideBar: {
      toolPanels: ["columns"],
    },
  };

  useEffect(()=>{ 
    if (columnState?.length && colDef.length > 0) {
        const result = currentGridRef?.current?.api.applyColumnState({
            state: columnState,
            applyOrder: true
        });
        if (!result) {
            console.error('Failed to apply column state');
        }
    }
  },[columnState,currentGridRef]);

  return (

    

    <VFTable
      ref={gridRef}
      animateRows={true}
      gridOptions={options}
      height={"400px"}
      disableZoomScaling={true}
      columnDefs={options.columnDefs}
      rowData={rowData}
      // pagination={true}
      statusBar = {{
        statusPanels: [
          { statusPanel: CustomStatusPanel, align: "left" },
        ],
      }} 
    
      onGridReady={(params: any) => {
        params.api.autoSizeAllColumns();
        setCurrentGridRef(gridRef);
        params.api.addEventListener('filterChanged', () => {
          const filterModel = params.api.getFilterModel();
          if (Object.keys(filterModel).length > 0) {
              setIsDisabled(false); 
          } else {
              setIsDisabled(true); 
          }
          });
      }}

      />
      
  );
};

export default DayWiseCoverageTable;
