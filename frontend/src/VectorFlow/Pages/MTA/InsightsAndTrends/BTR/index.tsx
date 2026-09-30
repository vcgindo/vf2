import { BTRLayoutTabsWrapper, BTRLayoutWrapper, ToggleViewBtnWrapper } from "./styles";
import useBTR from "./useBTR";
import { SCViewBackground, SCViewContainer, SCViewImage, SCVerticalDivider } from '../../SupplyChainIntelligenceHub/Planning/ActionToolBar/styles';
import { GridStateContext } from "../../../../../context/GridStateContext";
import VFFloatingTab from "../../../../../components/VectorFLOW/commons/VFFloatingTab";
import ActionToolBar from "../../SupplyChainIntelligenceHub/Planning/ActionToolBar";
import VFTable from "../../../../../components/VectorFLOW/commons/VFTable";
import LastRunDateComponent from "../../../../../components/commons/lastRundate";
import DailyDataGraphModal from "../../../../../components/VectorFLOW/commons/DailyDataGraphModal"
import OverlayLoader from "../../../../../VectorFlow/Pages/MTO/Common/Loader";
import NormChangeHistoryTable from "../../../../../components/VectorFLOW/commons/NormChangeHistoryTable";

const BufferTrendReport = () => {

    const {
        currentTab,
        isLoading,
        techColDefs,
        ecoRef,
        techRef,
        techTotalRows,
        verticalView,
        toggleVerticalView,
        toggleCurrentTab,
        renderView,
        tempRef,
        onExportToExcelCallBack,
        tempDownloadData,
        setTempDownloadData,
        tempAgGridProps,
        exportExcelRowData,
        showNormChangeHistoryTable,
        setExportExcelRowData,
        exportExcelColumns,
        setExportExcelColumns,
        currFilter,
        dailyData,
        setCurrFilter,
        onDeleteFilter,
        onApplyFilter,
        themeUi,
        horizon,
        ecoColDefs,
        setHorizon,
        lastRunDate,
        showDailyDataGraphModal,
        onResetCallback
    } = useBTR()

    

    return (
        <GridStateContext.Provider
            value={{
                ref: currentTab.id === "1" ? techRef : currentTab.id === "2" ? ecoRef : "",
                exportExcelColumns: exportExcelColumns,
                setExportExcelColumns: setExportExcelColumns,
                tempDownloadData: tempDownloadData,
                setTempDownloadData: setTempDownloadData,
                exportExcelRowData: exportExcelRowData,
                setExportExcelRowData: setExportExcelRowData,
                onResetCallback: onResetCallback
            }}
        >
            <div style={{zoom:0.9,marginLeft:'10px'}}>
                <ActionToolBar 
                    view={'grid'} 
                    setCurrentTab={''} 
                    currCategory={'BTR'} 
                    currentTab={currentTab.value} 
                    tabsList={[]} 
                    onFloatingTabChange={()=>console.log('')} 
                    onGoBack={()=>console.log('')} 
                    onViewChange={()=>console.log('')} 
                    onExportToExcelCallBack={(pageNumber:number)=>{return onExportToExcelCallBack(pageNumber,currentTab.value)}}
                    genericRecordCount={parseInt(techTotalRows)}
                    multiFilter={currFilter}
                    lastRunDate={lastRunDate}
                    setMultiFilter={setCurrFilter}
                    onDelete={onDeleteFilter}
                    onApplyFilter={onApplyFilter}
                    horizon={horizon}
                    onChangeHorizon={(value:number)=>setHorizon(value)}
 
                />
            </div>
            {lastRunDate && (
                <LastRunDateComponent lastRunDate={lastRunDate} />
            )}
             {
            showDailyDataGraphModal && <DailyDataGraphModal rowData={dailyData.rowData} chartData={dailyData.chartData} normChangeData={dailyData.normChangeData} masterData={dailyData.masterData} isModalOpen={showDailyDataGraphModal} suggestionData={dailyData.suggestionData} monitoringData={dailyData.monitoringData} skuKey={'SKUCode'} whKey={'LocationName'} />
        }
        {
            showNormChangeHistoryTable && <NormChangeHistoryTable data={dailyData.normChangeData} />
        }
        <BTRLayoutWrapper>
                <BTRLayoutTabsWrapper>
                    <div style={{ zoom: 0.6}}>
                        <VFFloatingTab
                            handleClick={(tab: any) => toggleCurrentTab(tab)}
                            tabs={[
                                {
                                    id: "1",
                                      value: 'on-hand',
                                    label: "On-Hand Inv. View"
                                  
                                },
                                {
                                    id: "2",
                                     value: 'pipeline',
                                    label: "Pipeline Inv. View"
                                   
                                },
                                {
                                    id: "3",
                                     value: 'both',
                                    label: "Both On-Hand & Pipeline View"
                                }
                            ]}
                        />
                    </div>
                    {currentTab?.id === '3' && (
                        <ToggleViewBtnWrapper>
                            <SCViewBackground>
                                <SCViewContainer onClick={() => toggleVerticalView(true)}>
                                    <SCViewImage src={verticalView?themeUi==="REGALBLAZE"?"/assets/img/VectorFLOW/BPR/grid-view-regal.svg":"/assets/img/VectorFLOW/BPR/grid-view-pink.svg":"/assets/img/VectorFLOW/BPR/grid-view-grey.svg"} style={{ transform: 'rotate(90deg)' }} alt="" />
                                    <p style={{ color: verticalView?themeUi!=="REGALBLAZE"? '#bc3d81':'#FCA311':'gray' }}>Vertical View</p>
                                </SCViewContainer>
                                <div><SCVerticalDivider /></div>
                                <SCViewContainer onClick={() => toggleVerticalView(false)} >
                                    <SCViewImage src={!verticalView?themeUi==="REGALBLAZE"?"/assets/img/VectorFLOW/BPR/grid-view-regal.svg":"/assets/img/VectorFLOW/BPR/grid-view-pink.svg":"/assets/img/VectorFLOW/BPR/grid-view-grey.svg"} alt="" />
                                    <p style={{ color: !verticalView?themeUi!=="REGALBLAZE"? '#bc3d81':'#FCA311':'gray' }}>Horizontal View</p>
                                </SCViewContainer>
                            </SCViewBackground>
                        </ToggleViewBtnWrapper>
                    )}
                </BTRLayoutTabsWrapper>
                {isLoading && <OverlayLoader />}
                {!isLoading && renderView()}
                <div style={{ display: 'none' }}>
                    <VFTable
                        ref={tempRef}
                        columnDefs={currentTab.id==='2'?techColDefs:ecoColDefs}
                        rowData={exportExcelRowData}
                        {...tempAgGridProps}
                        maintainColumnOrder={true}
                    />
                </div>
            </BTRLayoutWrapper>
        </GridStateContext.Provider>
    );
};

export default BufferTrendReport;
