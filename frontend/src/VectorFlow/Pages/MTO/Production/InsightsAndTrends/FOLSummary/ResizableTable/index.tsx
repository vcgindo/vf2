import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import { ColDef } from "ag-grid-enterprise";
import { useEffect, useState } from "react";
import CustomPageSizeInput from "../../../../../../../VectorFlow/Pages/MTO/Common/VFPagination/CustomPageSizeInput";
import VFTable from "../../../../../../../VectorFlow/Pages/MTO/Common/VFTable";
import { VFTableWrapper } from './style';
import { GridFilterWrapper, TextBtn } from "../../../../Common/VFPagination/styles";
import { useUserData } from "../../../../../../../context/index";



interface IResizeTableProps {
  colDef: ColDef[];
  data: any;
  setCurrentGridRef: any;
  currentGridRef: any;
  columnState: any;
  gridRef: any;
  userPageSize: number;
  savePageSize: any;
  isPivot?: boolean;
}

const ResizableTable = (props: IResizeTableProps) => {
  const {
    data, colDef, setCurrentGridRef, currentGridRef, columnState,
    userPageSize, savePageSize, isPivot
  } = props;

    const gridRef = props.gridRef;
    const [isDisabled, setIsDisabled]= useState<boolean>(true)
    const { user } = useUserData();
    const theme_ui = user.user.theme_ui
      

  const getRowStyle = (params: any) => {
    return { background: params.node.rowIndex % 2 === 0 ? "white" : "#F4F4F4" };
  };

  const defaultColDef = {
    filter: "agTextColumnFilter",
    floatingFilter: true,
    floatingFilterComponentParams: { suppressFilterButton: true },
    suppressMenu: true,
    resizable: true,
    cellStyle: {
      textAlign: 'center',
      fontStyle: "normal",
      fontVariant: "normal",
      fontSize: "20px",
      fontFamily: "Roboto",
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
      resizable: 'true',
    },
    flex: 1,
  };

  useEffect(() => {
    if (currentGridRef?.current && columnState?.length) {
      const applyPivot = currentGridRef.current?.api.setGridOption(
        "pivotMode",
        isPivot
      );
      const result = currentGridRef.current.api.applyColumnState({
        state: columnState,
        applyOrder: true
      });
      if (!result || !applyPivot) console.error('Failed to apply column state');
    }
  }, [columnState]);


  const customPage = () => (
    <div style={{ display: 'flex', justifyContent: 'end', gap: '1rem', width: '100%',paddingBottom: '3px' }}>
      <CustomPageSizeInput
        savePageSize={savePageSize}
        userPageSize={userPageSize}
      />
    </div>
  );

    const clearGridFilter = () =>{
      gridRef?.current?.api.setFilterModel(null);
        setIsDisabled(true);
  }
  
    const CustomStatusPanel = () => {
          return (
              <GridFilterWrapper>
                  <TextBtn  onClick={clearGridFilter} style={{marginTop:'15px'}} disabled={isDisabled} themeUi={theme_ui}>
                      Clear All Grid Filters
                  </TextBtn>  
              </GridFilterWrapper>           
          );
      }; 

  return (
    <VFTableWrapper>
      <VFTable
        ref={props.gridRef}
        columnDefs={colDef}
        rowData={data}
        defaultColDef={defaultColDef}
        getRowStyle={getRowStyle}
        statusBar={{
          statusPanels: [{ statusPanel: customPage, align:'right' },
            { statusPanel: CustomStatusPanel, align: "left" },
              { statusPanel: "agTotalAndFilteredRowCountComponent", align: "left"  },
              { statusPanel: "agTotalRowCountComponent", align: "left"  },
              { statusPanel: "agFilteredRowCountComponent", align: "left"  },
              { statusPanel: "agSelectedRowCountComponent", align: "left"  },
        
              {
                statusPanel: "agAggregationComponent",
                align:'left',
                statusPanelParams: {
                    aggFuncs: ["avg", "sum", "min", "max", "count",  ],
                },
            },
          ],
        }}
        pagination={true}
        paginationPageSize={userPageSize}
        paginationPageSizeSelector={false}
        onGridReady={(params: any) => {
          params.api.autoSizeAllColumns();
          setCurrentGridRef(props.gridRef);
          params.api.addEventListener('filterChanged', () => {
            const filterModel = params.api.getFilterModel();
            if (Object.keys(filterModel).length > 0) {
                setIsDisabled(false); 
            } else {
                setIsDisabled(true); 
            }
            });
        }}

        maintainColumnOrder
      />
    </VFTableWrapper>
  );
};

export default ResizableTable;
