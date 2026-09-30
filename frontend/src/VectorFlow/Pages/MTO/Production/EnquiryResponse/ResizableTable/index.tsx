import { ColDef } from "ag-grid-enterprise";
import React, { useEffect, useRef, useState } from "react";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import VFTable from "../../../Common/VFTable";
import { VFTableWrapper } from "./styles";
import { GridFilterWrapper, TextBtn } from "../../../Common/VFPagination/styles";
import { useUserData } from "../../../../../../context";
import CustomPageSizeInput from "../../../../../../VectorFlow/Pages/MTO/Common/VFPagination/CustomPageSizeInput";


interface IResizeTableProps {
  colDef: ColDef[];
  data: any;
  setCurrentGridRef: any,
  currentGridRef: any,
  columnState: any,
  gridRef: any,
  userPageSize: number;
  savePageSize: any;
}

const ResizableTable = (props: IResizeTableProps) => {
  const { data, colDef, setCurrentGridRef, currentGridRef, columnState, userPageSize, savePageSize } = props;
  const gridRef = props.gridRef;
  const [isDisabled, setIsDisabled]= useState<boolean>(true)
  const { user } = useUserData();
  const theme_ui = user.user.theme_ui
  

  const getRowStyle = (params: any) => {
    if (params.node.rowIndex % 2 === 0) {
      return { background: "white" };
    }
    return { background: "#F4F4F4" };
  };

  const defaultColDef = {
    filter: "agTextColumnFilter",
    floatingFilter: true,
    suppressMenu: true,
    resizable: true,
    cellStyle: {
      'text-align': 'center',
      "font-style": "normal",
      "font-variant": "normal",
      "font-size": "20px",
      'font-weight': "300",
      "font-family": "Roboto",
      'text-overflow': 'ellipsis',
      'white-space': 'nowrap',
      'resizable': 'true',
    },
    flex: 1,
  };

  const clearGridFilter = () =>{
    gridRef?.current?.api.setFilterModel(null);
      setIsDisabled(true);
}

  const CustomStatusPanel = () => {
        return (
            <GridFilterWrapper style={{marginTop:'15px', paddingTop:'3px'}}>
                <TextBtn onClick={clearGridFilter} disabled={isDisabled} themeUi={theme_ui}>
                    Clear All Grid Filters
                </TextBtn>  
            </GridFilterWrapper>           
        );
    };  

  useEffect(()=>{ 
    if (currentGridRef?.current && currentGridRef.current.api && columnState?.length) {
      const result = currentGridRef.current.api.applyColumnState({
        state: columnState,
        applyOrder: true
      });
      if (!result) {
        console.error('Failed to apply column state');
      }
    }
  }, [columnState]);





  const customPage = () => (
    <div>
      <CustomPageSizeInput 
        savePageSize={savePageSize}
        userPageSize={userPageSize}
      />
    </div>
  );
  
  return (
    <VFTableWrapper >
      <VFTable
        ref={gridRef}
        columnDefs={colDef}
        rowData={data}
        defaultColDef={defaultColDef}
        getRowStyle={getRowStyle}
        pagination={true}
        gridOptions={{
          sideBar: {
            toolPanels: ["agColumnsToolPanel"],
          },
        }}
        maintainColumnOrder
        
        statusBar = {{
          statusPanels: [
            { statusPanel: CustomStatusPanel, align: "left" },
            { statusPanel: 'agTotalAndFilteredRowCountComponent', align:'left' },
            {
              statusPanel: "agAggregationComponent",
              align: "left", 
              statusPanelParams: {
                  aggFuncs: ["avg", "sum", "max", "min", "count"],
              },
          },
            { statusPanel: customPage, align:'right' }
          ],
        }}  
        paginationPageSize={userPageSize}
        paginationPageSizeSelector={false}        
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
    </VFTableWrapper>

  );
};

export default React.memo(ResizableTable);
