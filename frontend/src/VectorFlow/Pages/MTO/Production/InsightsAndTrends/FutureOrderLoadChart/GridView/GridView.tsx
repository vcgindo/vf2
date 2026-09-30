import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import VFTable from "../../../../../../../VectorFlow/Pages/MTO/Common/VFTable";
import { useEffect, useRef, useState } from "react";
import { TabsSection,MyFutureOrderTabsFix } from "../styles";
import VFFloatingTab from '../../../../../../../components/VectorFLOW/commons/VFFloatingTab';
import { ApplyZoomOut } from '../../../OrderRescheduling/styles';
import CustomPageSizeInput from "../../../../../../../VectorFlow/Pages/MTO/Common/VFPagination/CustomPageSizeInput";
import { GridFilterWrapper, TextBtn } from "../../../../../../../VectorFlow/Pages/MTO/Common/VFPagination/styles";
import { useUserData } from "../../../../../../../context/index";
import { VFTableWrapper } from "./style";
import LoadTagTooltip from "../LoadTagToolTip";


const GridView = ({ setCurrentGridRef,context, currentGridRef,Viewtabs, columnState, colDef, userPageSize , savePageSize, rowData, setCurrView, currView, currTab, selectedAction, isGridView }: any) => {
    const gridRef = useRef<any>(null);
    const [isDisabled, setIsDisabled] = useState<boolean>(true)
    const { user } = useUserData();
    const theme_ui = user.user.theme_ui

  const agGridProps = {
    defaultColDef: {
      autoHeaderHeight: true,
      filter: "agMultiColumnFilter",
      floatingFilter: true,
      enableRowGroup: true,
      floatingFilterComponentParams: { suppressFilterButton: false },
      tooltipComponent: LoadTagTooltip,
      initialWidth: 110,

    },
    cellStyle: {
        'text-align': 'center',
        'height': '50px',
        "font-style": "normal",
        "font-variant": "normal",
        "font-size": "12px",
        "font-family": "Roboto",
        'text-overflow': 'ellipsis',
        'white-space': 'nowrap',
        'resizable': 'true',

    },
  }

   
        useEffect(() => {
          if (currentGridRef?.current && columnState?.length ) {
            const isLoadWise = currTab === 'Load Wise';
            const isANS = selectedAction?.value === 'ANS';
            const currentGridIndex =  isLoadWise
            ? isANS 
              ? 0
              : 1
            : isANS
              ? 2
                : 3;
            
                const result = currentGridRef.current.api.applyColumnState({
                    state: columnState[currentGridIndex],
                    applyOrder: true
                });
                if (!result) {
                    console.error('Failed to apply column state');
                }
            }
        },[currentGridRef, columnState, isGridView,currTab, selectedAction]);

     const clearGridFilter = () =>{
          gridRef?.current?.api.setFilterModel(null);
            setIsDisabled(true);
      }
      
        const CustomStatusPanel = () => {
              return (
                  <GridFilterWrapper style={{marginTop:'15px'}}>
                      <TextBtn  onClick={clearGridFilter}  disabled={isDisabled} themeUi={theme_ui}>
                          Clear All Grid Filters
                      </TextBtn>  
                  </GridFilterWrapper>           
              );
    }; 
    
    const customPage = () => (
      <div style={{ display: 'flex', justifyContent: 'end', gap: '1rem', width: '100%',paddingBottom: '3px' }}>
        <CustomPageSizeInput
          savePageSize={savePageSize}
          userPageSize={userPageSize}
        />
      </div>
    );

  const getRowStyle = (params: any) => {
    if (params.node.rowIndex % 2 === 0) {
      return { background: "white" };
    }
    return { background: "#F4F4F4" };
  };

    return (
        <>
            <TabsSection style={{paddingTop:'6px', marginTop:'10px'}}>
                <ApplyZoomOut>
                    <MyFutureOrderTabsFix>
                    <VFFloatingTab style={{minWidth:'0px'}}
                        handleClick={(e) => setCurrView(e.id)}
                        tabs={Viewtabs}
                         defaultTab={Viewtabs.findIndex((tab:any) => tab.id === currView) || 0}
                        />
                    </MyFutureOrderTabsFix>
              </ApplyZoomOut>
            </TabsSection>
            
            <VFTableWrapper style={{height: '72vh', marginTop: '20px', paddingLeft: '25px'}}>
          <VFTable 
            {...agGridProps}
                    columnDefs={colDef}
                    rowData={rowData}
                    getRowStyle={getRowStyle}
                    tooltipHideDelay={100000}
                    gridOptions={{
                        sideBar: {
                          toolPanels: ["agColumnsToolPanel"],
                        },
                      }}
                    tooltipShowDelay={0}
                    statusBar={{
                        statusPanels: [{ statusPanel: customPage, align:'right' },
                        { statusPanel: CustomStatusPanel, align: "left" },
                        { statusPanel: 'agTotalAndFilteredRowCountComponent', align:'left' },
                        {
                          statusPanel: "agAggregationComponent",
                          align: "left", 
                          statusPanelParams: {
                              aggFuncs: ["avg", "sum", "max", "min", "count"],
                          },
                      },
                        ],
                      }}
                    tooltipMouseTrack={true}
                    pagination={true}
                    paginationPageSize={userPageSize}
                    paginationPageSizeSelector={false}
                    ref={gridRef}
                    context={context}
                    maintainColumnOrder
                    onGridReady={(params: any) => {
                      params.api.autoSizeAllColumns();
                        setCurrentGridRef(gridRef);
                      }}
                    onFilterChanged={()=>{Object.keys((currentGridRef?.current?.api?.getFilterModel()))?.length>0 ? setIsDisabled(false) : setIsDisabled(true)}}
                />
            </VFTableWrapper>
         </>
    )
}

export default GridView