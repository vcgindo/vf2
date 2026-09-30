
import VFTable from "../../../../../VectorFlow/Pages/MTO/Common/VFTable"
import { BPRLayout, LastRunDateHeader, LastRunDate, Wrapper } from "./styles"
import BPRViewTable from "./BPRViewTable"
import { Allotment } from "allotment"
import useBPR from "./useBPR"

import "allotment/dist/style.css";
import ActionToolBar from "../Planning/ActionToolBar"
import DailyDataGraphModal from "../../../../../components/VectorFLOW/commons/DailyDataGraphModal"
import NormChangeHistoryTable from "../../../../../components/VectorFLOW/commons/NormChangeHistoryTable"
import { GridStateContext } from "../../../../../context/GridStateContext"
import BPRRemarkHistoryModal from "./BPRRemarkHistoryModal"
import { Skeleton } from "../../../../../components/commons/styled";
import VFSaveRemark from "../../../../../components/VectorFLOW/commons/VFSaveRemark"
import { useMemo, useState } from "react"
import LastRunDateComponent from "../../../../../components/commons/lastRundate";
import OverlayLoader from "../../../../../VectorFlow/Pages/MTO/Common/Loader"
import VFPagination from "../../../../../VectorFlow/Pages/MTO/Common/VFPagination"

const BPR = ()=>{


  const {
        // isSideBarOpen,
        isSubGridOpen,
        isLoading ,
        activeRow,
        BPRColumns,
        BPRRowData,
        agGridProps,
        isRemarkHistoryToolTipOpen,
        remarkHistory,
        onSubmitRemarks,
        onCloseRemarkHistory,
        dailyData,
        showDailyDataGraphModal,
        showNormChangeHistoryTable,
        handleOnPageChange,
        recordCount,
        currGridPage,
        rowsPerPage,
        ref,
        isSavedDataLoading,
        tempRef,
        tempDownloadData,
        setTempDownloadData,
        tempAgGridProps,
        exportExcelRowData,
        setExportExcelRowData,
        exportExcelColumns,
        setExportExcelColumns,
        onExportToExcelCallBack,
        currFilter,
        setCurrFilter,
        onApplyFilter,
        editedRows,
        onDeleteFilter,
        lastRunDate,
        generalFilterOptions,
      onResetCallback,
      savePageSize,
      userPageSize,
    } = useBPR();

    const [isDisabled, setIsDisabled]= useState<boolean>(true)
 
    // if(isLoading || isSavedDataLoading){
    //   return (
    //     <VFLoader/>
    //   )
    // }

    const Statusbar = useMemo(()=>{
        return {
            statusPanels: [
              { statusPanel: 'agTotalAndFilteredRowCountComponent', align:'left' },
              { statusPanel: 'agTotalRowCountComponent', align:'left' },
              { statusPanel: 'agFilteredRowCountComponent', align:'left' },
              { statusPanel: 'agSelectedRowCountComponent', align:'left' },
              { statusPanel: 'agAggregationComponent', align:'left' },
            ],
          }
    },[])

    

    return(
        <GridStateContext.Provider
            value={{
                ref:ref,
                exportExcelColumns:exportExcelColumns,
                setExportExcelColumns:setExportExcelColumns,
                tempDownloadData:tempDownloadData,
                setTempDownloadData:setTempDownloadData,
                exportExcelRowData:exportExcelRowData,
                setExportExcelRowData:setExportExcelRowData,
                onResetCallback:onResetCallback
    
            }}
        >
        <div style={{marginLeft:'10px'}}>
        <ActionToolBar 
            view={'grid'} 
            setCurrentTab={''} 
            currCategory={'BPR'} 
            currentTab={''} 
            tabsList={[]} 
            onFloatingTabChange={()=>console.log('')} 
            onApplyFilter={(e)=>onApplyFilter(e)}
            onGoBack={()=>console.log('')} 
            onViewChange={()=>console.log('')} 
            genericRecordCount={recordCount}
            onExportToExcelCallBack={onExportToExcelCallBack}
            multiFilter={currFilter}
            onDelete={onDeleteFilter}
            setMultiFilter={setCurrFilter}
            onSubmitEditedRows={onSubmitRemarks}
            disableSubmitEditedRowsBtn={editedRows.length===0}
            lastRunDate={lastRunDate}
            generalFilterOptions={generalFilterOptions}
        />
        </div>
        {lastRunDate && (
        <LastRunDateComponent lastRunDate={lastRunDate} />
      )}
        {
            showDailyDataGraphModal && <DailyDataGraphModal rowData={dailyData.rowData} chartData={dailyData.chartData} normChangeData={dailyData.normChangeData} masterData={dailyData.masterData} isModalOpen={showDailyDataGraphModal} suggestionData={dailyData.suggestionData} monitoringData={dailyData.monitoringData} skuKey={'SKUCode'} whKey={'WHName'} />
        }
        {
            showNormChangeHistoryTable && <NormChangeHistoryTable data={dailyData.normChangeData} />
        }
        
        {(isLoading || isSavedDataLoading) && <OverlayLoader/> }
            <BPRLayout>
            {/* <BPRTaskBar style={{width:isSideBarOpen?'77%':'97%'}}>
                <VFButtonOutline
                    themeUi="NOIRFUSION"
                    onClick={()=>console.log('')}
                >
                    Excel Export 
                </VFButtonOutline>
                <VFButton
                    themeUi="NOIRFUSION"
                    onClick={()=>console.log('')}
                >
                    Edit Filter
                </VFButton>
            </BPRTaskBar> */}
            <div style={{height:'100vh',marginLeft:'15px'}}>
            <Allotment vertical defaultSizes={[300,150]}>
              <Allotment.Pane className="planning-grid-allotment">
              <Wrapper>
              <VFTable    
                 key={'ref'}
                disableZoomScaling
                ref={ref}
                height={"100%"}
                {...agGridProps}
                columnDefs={BPRColumns}
                rowData={BPRRowData}
                maintainColumnOrder
                enableRangeSelection={true} 
                rowSelection="multiple"
                statusBar = {Statusbar}
                tooltipShowDelay={500}
                onFilterChanged={() => {
                    const filterModel = ref?.current?.api?.getFilterModel();
                    if (filterModel && Object.keys(filterModel).length > 0) {
                      setIsDisabled(false);
                    } else {
                      setIsDisabled(true);
                    }
                }}
                  
            />
              </Wrapper>
              
                {BPRRowData?.length > 0 && 
                <>
                <VFPagination
                    selectedRows={0}
                    totalRows={recordCount}
                    currentPage={currGridPage}
                    rowsPerPage={userPageSize}
                    handleChangePage={handleOnPageChange}
                    resetGridRef={ref} 
                    isDisabled={isDisabled}
                    customPageSizeEnabled={true}
                    userPageSize={userPageSize}
                    savePageSize={savePageSize}
                />
                <VFSaveRemark onSubmitRemarks={onSubmitRemarks} />
                </>
                }
              {/* {onSubmitRemarks && (
                 <CustomizedOutlineWrapper style={{ margin: '1rem 0', padding: 0 }}>
                    <VFButtonOutline 
                    style={{height:'30px',width:'159px',borderRadius:'4px',fontSize:'14px',fontWeight:'400',cursor:'pointer'}}
                        themeUi={themeUi} 
                        onClick={onSubmitRemarks}
                            >
                        Save Remark
                        </VFButtonOutline>
                  </CustomizedOutlineWrapper>
               )} */}
              </Allotment.Pane>
              <Allotment.Pane maxSize={350} minSize={200}>
              <div style={{marginTop:'20px'}}>
              {isSubGridOpen && (
                <div style={{marginLeft:'15px',zoom:0.8}}>
                    <BPRViewTable
                tableHeader="In Transit/WIP"
                    tablePrefixSrc="/assets/img/VectorFLOW/BPR/in-transit.svg"
                    rowData={activeRow}
                    colDefs={[
                        {
                            headerName:"LR Code",
                            colId:'lc',
                            field:'lc'
                        },
                        // {
                        //     headerName:"Creation Date",
                        //     colId:'cd',
                        //     field:'cd'
                        // },
                        {
                            headerName:"Ageing",
                            colId:'ag',
                            field:'ag'
                        },
                        // {
                        //     headerName:"ETA",
                        //     colId:'eta',
                        //     field:'eta'
                        // },
                        // {
                        //     headerName:"Current Location",
                        //     colId:'cl',
                        //     field:'cl'
                        // },
                        {
                            headerName:"Quantity",
                            colId:'qty',
                            field:'qty'
                        },
                        {
                            headerName:"Whereabouts",
                            colId:'whereabouts',
                            field:'whereabouts'
                        }
                        // {
                        //     headerName:"Execution Eco Color",
                        //     colId:'exeecocolor',
                        //     field:'exeecocolor'
                        // },
                        // {
                        //     headerName:"Remarks",
                        //     colId:'remarks',
                        //     field:'remarks'
                        // }
                    ]
                }

                    
                />
                </div>
               
            )}
              </div>
              </Allotment.Pane>
            </Allotment>
            </div>
            {/* {isSubmitRemarkToolTipOpen && (
                <BPRSubmiRemarkToolTip
                    remark={remark}
                    setRemark={updateRemark}
                    style={submitRemarkToolTipPosition}
                    onSuccess={onSubmitRemark}
                    onClose={onCloseSubmitRemark}
                    themeUi={themeUi}
                />
            )} */}

            <BPRRemarkHistoryModal
                data={remarkHistory}
                isOpen={isRemarkHistoryToolTipOpen}
                onClose={onCloseRemarkHistory}
            />
            <div style={{display:'none'}}>                
                  <VFTable
                  
                    key={'temp'}
                    ref={tempRef}
                    columnDefs={BPRColumns}
                    rowData={exportExcelRowData}
                    {...tempAgGridProps}

                  
                  />
                </div>
        </BPRLayout>
        </GridStateContext.Provider>
    )
            }

export default BPR
