import React,{useCallback, useState} from 'react'

import {DayPicker} from 'react-day-picker'
import { Player } from '@lottiefiles/react-lottie-player'

import VFCapsule from "../../../../../components/VectorFLOW/commons/VFCapsule"
import VFRangeSlider from "../../../../../components/VectorFLOW/commons/VFRangeSlider"
import VFTable from "../../../../../components/VectorFLOW/commons/VFTable"


import { AvailabilityTrendHeader,ChartHeaderRadioGroup,ResearchInsightsTableWrapper, AvailabilityTrendWrapper, ResearchInsightsLayout,AvailabilityTrendSection, HistoricalAvailabiltyHeader, HistoricalAvailabiltyContent, HistoricalAvailabiltyContentSection, HistoricalAvailabiltyContentSectionHeader, HistoricalAvailabiltyContentSectionData, HorizonHeader, ChartHeader, ChartHeaderText, CapsuleWrapper, CalenderWrapper, CalenderHeader, ChartWrapper, CalenderSummaryWrapper, CalenderSummaryCell, CalenderSummaryCellText, CalenderSummaryCellContentWrapper, CalenderSummaryCellContent, CalenderSummaryCellContentStick, ExpandChartIcon, RadioGroup, DefaultViewRendererWrapper, DefaultViewRendererHeader, DefaultViewRendererText } from "./styles"

import CustomCalenderCaption from './CustomCalenderCaption'
import CustomCalenderDay from './CustomCalenderDay'
import useResearchInsights from './useResearchInsights'

import 'react-day-picker/dist/style.css';
import './styles.css'
import { AgCharts } from 'ag-charts-react'
import ActionToolBar from '../../SupplyChainIntelligenceHub/Planning/ActionToolBar'
import ExpandedGraph from './ReseachInsightsExpandedGraph'
import VFPagination from "../../../../../VectorFlow/Pages/MTO/Common/VFPagination"
import { GridStateContext } from '../../../../../context/GridStateContext'
import DailyDataGraphModal from "../../../../../components/VectorFLOW/commons/DailyDataGraphModal"
import NormChangeHistoryTable from "../../../../../components/VectorFLOW/commons/NormChangeHistoryTable"
import VFButton from '../../../../../components/VectorFLOW/commons/VFButton'
import { useUserData } from '../../../../../context'
import { Skeleton } from '../../../../../components/commons/styled'
import LastRunDateComponent from "../../../../../components/commons/lastRundate";
import OverlayLoader from '../../../../../VectorFlow/Pages/MTO/Common/Loader'


const ResearchInsights = ()=>{

    const {
        ref,
        agGridProps,
        ResearchInsightsColumns,
        ResearchInsightsData,
        isLoading,
        isUpdatedGraphDataLoading,
        horizon,
        graphState,
        setHorizon,
        getColor,
        setCalenderType,
        handleOnUpdateGraph,
        redCount,
        blackCount,
        whiteCount,
        expandedGraphId,
        isGraphOneOpen,
        selfGraphData,
        locationGraphData,
        graphs,
        setGraphs,
        calenderType,
        expandedGraphAllFilterValues,
        toggleGraphModal,
        setIsGraphOneOpen,
        updateGraphState,
        recordCount,
        rowsPerPage,
        currGridPage,
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
        showDailyDataGraphModal,
        showNormChangeHistoryTable,
        dailyData,
        handlePageChange,
        onApplyFilter,
        onDeleteFilter,
        currentFilter,
        setCurrentFilter,
        historicalAvailabilityData,
        isHistoricalAvailabilityLoading,
        continuousBlack,
        continuousBlackAndRed,
        continuousWhite,
        generalFilterOptions,
        onResetCallback,
        lastRunDate,
        savePageSize,
        userPageSize
    } = useResearchInsights()

    const {user} = useUserData()
    const themeUi = user.user.theme_ui   
    const [isDisabled, setIsDisabled]= useState<boolean>(true)
    


    const getFormattedPercentage = useCallback((number: number) => {
        if (number === 0) return "0"; 
        if (number == null || isNaN(number)) return "-"; 
        return number.toFixed(2);
    }, []);



    return(
        <GridStateContext.Provider value={{
            ref:ref,
            exportExcelColumns:exportExcelColumns,
            setExportExcelColumns:setExportExcelColumns,
            tempDownloadData:tempDownloadData,
            setTempDownloadData:setTempDownloadData,
            exportExcelRowData:exportExcelRowData,
            setExportExcelRowData:setExportExcelRowData,
            onResetCallback:onResetCallback

        }}>
            <div style={{zoom:0.9, paddingLeft:'20px'}}>
       <ActionToolBar 
            view={'grid'} 
            setCurrentTab={''} 
            currCategory={'ResearchInsight'} 
            currentTab={''} 
            tabsList={[]} 
            onFloatingTabChange={()=>console.log('')} 
            onGoBack={()=>console.log('')} 
            onViewChange={()=>console.log('')}
            genericRecordCount={recordCount || 0}
            onExportToExcelCallBack={onExportToExcelCallBack}
            onApplyFilter={onApplyFilter}
            multiFilter={currentFilter}
            setMultiFilter={setCurrentFilter}
            onDelete={onDeleteFilter}
            lastRunDate={lastRunDate}
            generalFilterOptions={generalFilterOptions}
            onUpdateInsight={handleOnUpdateGraph}
            hideUpdateInsightsBtn={graphState==='default'}
        />
        </div>
        {lastRunDate && (
        <LastRunDateComponent lastRunDate={lastRunDate} />
      )}
        
        
            <ResearchInsightsLayout>
            {
                showDailyDataGraphModal && <DailyDataGraphModal rowData={dailyData.rowData} chartData={dailyData.chartData} normChangeData={dailyData.normChangeData} masterData={dailyData.masterData} isModalOpen={showDailyDataGraphModal} suggestionData={dailyData.suggestionData} monitoringData={dailyData.monitoringData} skuKey={'SKUCode'} whKey={'WHName'} />
            }
            {
                showNormChangeHistoryTable && <NormChangeHistoryTable data={dailyData.normChangeData} />
            }
            <ResearchInsightsTableWrapper style={{ marginRight:'15px'}}>
                {(isLoading || isSavedDataLoading) && <OverlayLoader/>}
                    <React.Fragment>
                        <VFTable
                            height={"100%"}
                            {...agGridProps}
                            ref={ref}
                            columnDefs={ResearchInsightsColumns}
                            rowData={ResearchInsightsData}
                            enableRangeSelection={true} // Added property
                            rowSelection="multiple"
                            statusBar = {{
                                statusPanels: [
                                { statusPanel: 'agTotalAndFilteredRowCountComponent', align:'left' },
                                { statusPanel: 'agTotalRowCountComponent', align:'left' },
                                { statusPanel: 'agFilteredRowCountComponent', align:'left' },
                                { statusPanel: 'agSelectedRowCountComponent', align:'left' },
                                { statusPanel: 'agAggregationComponent', align:'left' },
                                ],
                            }}
                            maintainColumnOrder
                            onFilterChanged={() => {
                                const filterModel = ref?.current?.api?.getFilterModel();
                                if (filterModel && Object.keys(filterModel).length > 0) {
                                  setIsDisabled(false);
                                } else {
                                  setIsDisabled(true);
                                }
                            }}
                            tooltipShowDelay={500}
                        />
                    {
                    ResearchInsightsData?.length  > 0 &&
                        <VFPagination
                            selectedRows={0}
                            totalRows={recordCount || 0}
                            currentPage={currGridPage}
                            rowsPerPage={userPageSize}
                            handleChangePage={handlePageChange}
                            resetGridRef={ref} 
                            isDisabled={isDisabled}
                            customPageSizeEnabled={true}
                            userPageSize={userPageSize}
                            savePageSize={savePageSize}
                        />
                }
                    </React.Fragment>
                
                {/* <ResearchInsightsTableTaskBar>
                    <VFButton
                        themeUi={themeUi}
                        onClick={handleOnUpdateGraph}
                        // disabled={graphState==='default'}
                    >
                        Update Graph
                    </VFButton>

                </ResearchInsightsTableTaskBar> */}
            </ResearchInsightsTableWrapper>
            {
                isUpdatedGraphDataLoading
                ?
                <AvailabilityTrendWrapper>
                    <OverlayLoader/>
                </AvailabilityTrendWrapper>
                :
                <AvailabilityTrendWrapper>
                <AvailabilityTrendHeader themeUi={themeUi}>
                   On Hand Availability Trend
                </AvailabilityTrendHeader>
                <AvailabilityTrendSection style={{borderBottom:'dashed 2px #B2B2B2'}}>
                    <HistoricalAvailabiltyHeader>
                        Historical Availability
                    </HistoricalAvailabiltyHeader>
                    {(isHistoricalAvailabilityLoading)?(
                    <Skeleton
                        style={{height:35,width:'100%'}}
                    />
                    ):(
                        <HistoricalAvailabiltyContent>
                            <HistoricalAvailabiltyContentSection>
                                <HistoricalAvailabiltyContentSectionHeader>
                                    90-60 Days
                                </HistoricalAvailabiltyContentSectionHeader>
                                <HistoricalAvailabiltyContentSectionData>
                                    {getFormattedPercentage(historicalAvailabilityData.availability_01_30)}%
                                </HistoricalAvailabiltyContentSectionData>
                            </HistoricalAvailabiltyContentSection>
                            <HistoricalAvailabiltyContentSection>
                                <HistoricalAvailabiltyContentSectionHeader>
                                    60-30 Days
                                </HistoricalAvailabiltyContentSectionHeader>
                                <HistoricalAvailabiltyContentSectionData>
                                    {getFormattedPercentage(historicalAvailabilityData.availability_31_60)}%
                                </HistoricalAvailabiltyContentSectionData>
                            </HistoricalAvailabiltyContentSection>
                            <HistoricalAvailabiltyContentSection style={{border:"none"}}>
                                <HistoricalAvailabiltyContentSectionHeader>
                                    30-0 Days
                                </HistoricalAvailabiltyContentSectionHeader>
                                <HistoricalAvailabiltyContentSectionData>
                                    {getFormattedPercentage(historicalAvailabilityData.availability_61_90)}%
                                </HistoricalAvailabiltyContentSectionData>
                            </HistoricalAvailabiltyContentSection>
                        </HistoricalAvailabiltyContent>
                    )}
                </AvailabilityTrendSection>
                {(graphState==='default')?(
                    <AvailabilityTrendSection style={{display:'flex',flexDirection:'row',marginBottom:'5px',zoom:0.7,alignItems:'center',padding:0}}>
                        <DefaultViewRendererWrapper>
                            <Player src={themeUi==="REGALBLAZE"?'/assets/img/VectorFLOW/BPR/swipe pointer regal.json':'/assets/img/VectorFLOW/BPR/swipe pointer.json'} loop autoplay style={{transform:'rotate(-90deg)',height:70,width:70}}/>
                            <DefaultViewRendererHeader>
                                No Data To Show
                            </DefaultViewRendererHeader>
                            <DefaultViewRendererText>
                                Please select data from the grid on left to view more insights
                            </DefaultViewRendererText>
                            <VFButton themeUi={themeUi} onClick={handleOnUpdateGraph}>Load Insights</VFButton>
                        </DefaultViewRendererWrapper>
                    </AvailabilityTrendSection>
                ):(
                    <AvailabilityTrendSection style={{display:'flex',flexDirection:'row',marginBottom:'5px',marginTop:'-5px',zoom:0.7,alignItems:'center',padding:0,borderBottom:'dashed 3px #B2B2B2'}}>
                    <HorizonHeader style={{margin:'0px 0px 0px 30px'}}>
                        Horizon
                    </HorizonHeader>
                    <VFRangeSlider
                        showTriangle={false}
                        min={1}
                        max={90}
                        milestones={[0,1,90]}
                        strictMode={false}
                        width={250}
                        defaultValue={horizon}
                        handleChange={(e)=>setHorizon(e)}
                        style={{marginTop:0}}
                        labelValueFormatter={(value:number)=>value>1?`${value} Days`:`${value} Day`}
                    />
                </AvailabilityTrendSection>
                )}
                {graphState==='calender' && (
                    <React.Fragment>
                        <AvailabilityTrendSection>
                        <ChartHeader>
                            <ChartHeaderText>
                                Summary
                            </ChartHeaderText>
                            <CapsuleWrapper>
                                <VFCapsule
                                    activeBtn={{label:calenderType,value:calenderType}}
                                    capsules={[
                                        {
                                            label:"On-Hand Inventory",
                                            value:'Tech'
                                        },
                                        {
                                            label:"Pipeline Inventory",
                                            value:'Eco'
                                        }
                                    ]}
                                    handleClick={(e:any)=>setCalenderType(e.value)}
                                    
                                />
                            </CapsuleWrapper>
                        </ChartHeader>
                        <CalenderWrapper>
                            <CalenderHeader> {calenderType === 'Tech' ? 'On-Hand' : 'Pipeline'}  </CalenderHeader>
                            <DayPicker
                                style={{
                                    zoom:0.7
                                }}
                                mode='single'
                                components={{
                                    Caption:CustomCalenderCaption,
                                    Day:(props)=>{
                                        return <CustomCalenderDay {...props} color={getColor(props.date)}/>
                                    }
                                }}
                                styles={{
                                    cell:{
                                        padding:'5px',
                                    },

                                }}
                            />
                        </CalenderWrapper>
                    </AvailabilityTrendSection>
                    <AvailabilityTrendSection>
                        <CalenderSummaryWrapper>
                            <CalenderSummaryCell>
                                <CalenderSummaryCellText>Black Count</CalenderSummaryCellText>
                                <CalenderSummaryCellContentWrapper>
                                    <CalenderSummaryCellContent>
                                            {blackCount}%
                                    </CalenderSummaryCellContent>
                                    <CalenderSummaryCellContentStick style={{backgroundColor:'black'}}/>
                                </CalenderSummaryCellContentWrapper>
                            </CalenderSummaryCell>
                            <CalenderSummaryCell>
                                <CalenderSummaryCellText>Red Count</CalenderSummaryCellText>
                                <CalenderSummaryCellContentWrapper>
                                    <CalenderSummaryCellContent>
                                        {redCount}%
                                    </CalenderSummaryCellContent>
                                    <CalenderSummaryCellContentStick style={{backgroundColor:'#F04D4D'}}/>
                                </CalenderSummaryCellContentWrapper>
                            </CalenderSummaryCell>
                            <CalenderSummaryCell>
                                <CalenderSummaryCellText>White Count</CalenderSummaryCellText>
                                <CalenderSummaryCellContentWrapper>
                                    <CalenderSummaryCellContent>
                                            {whiteCount}%
                                    </CalenderSummaryCellContent>
                                    <CalenderSummaryCellContentStick style={{backgroundColor:'gray'}}/>
                                </CalenderSummaryCellContentWrapper>
                            </CalenderSummaryCell>
                        </CalenderSummaryWrapper>
                    </AvailabilityTrendSection>
                    <AvailabilityTrendSection style={{borderBottom:'none'}}>
                        <CalenderSummaryWrapper>
                            <CalenderSummaryCell>
                                <CalenderSummaryCellText style={{height:27}}>Contd. Black Ageing</CalenderSummaryCellText>
                                <CalenderSummaryCellContentWrapper>
                                    <CalenderSummaryCellContent>
                                        {continuousBlack}
                                    </CalenderSummaryCellContent>
                                </CalenderSummaryCellContentWrapper>
                            </CalenderSummaryCell>
                            <CalenderSummaryCell>
                                <CalenderSummaryCellText style={{height:27}}>Contd. Black + Red Ageing</CalenderSummaryCellText>
                                <CalenderSummaryCellContentWrapper>
                                    <CalenderSummaryCellContent>
                                        {continuousBlackAndRed}
                                    </CalenderSummaryCellContent>
                                </CalenderSummaryCellContentWrapper>
                            </CalenderSummaryCell>
                            <CalenderSummaryCell>
                                <CalenderSummaryCellText style={{height:27}}>Contd. White Ageing</CalenderSummaryCellText>
                                <CalenderSummaryCellContentWrapper>
                                    <CalenderSummaryCellContent>
                                        {continuousWhite}
                                    </CalenderSummaryCellContent>
                                </CalenderSummaryCellContentWrapper>
                            </CalenderSummaryCell>
                        </CalenderSummaryWrapper>
                    </AvailabilityTrendSection>
                    </React.Fragment>
                )}
                {graphState==='graph' && (
                    <React.Fragment>
                        <AvailabilityTrendSection style={{paddingBottom:'0'}}>
                    <ChartHeader>
                        <ChartHeaderText>
                            Current Location
                        </ChartHeaderText>
                        <CapsuleWrapper>
                            <VFCapsule
                                activeBtn={graphs[0].pen}
                                capsules={[
                                    {
                                        label:"On-Hand Inv.",
                                        value:'Tech'
                                    },
                                    {
                                        label:"Pipeline Inv.",
                                        value:'Eco'
                                    }
                                ]}
                                handleClick={(value:any)=>updateGraphState(1,'pen',value)}
                                
                            />
                        </CapsuleWrapper>
                    </ChartHeader>
                    <ChartWrapper>
                        <ExpandChartIcon src='/assets/img/VectorFLOW/BPR/expand-graph.svg' onClick={()=>toggleGraphModal(true,1)}/>
                        <AgCharts
                        options={{
                            height:200,
                            width:300,
                            data:selfGraphData,
                            axes:[
                                {
                                    
                                    type:"category",
                                    position:'bottom',
                                    label:{
                                        fontSize:8
                                    }
                                },
                                {
                                    type:"number",
                                    position:'left',
                                    label:{
                                        fontSize:8
                                    }
                                },
                                {
                                    type: "number",
                                    position: 'left',
                                    label: {
                                        fontSize: 8
                                    },
                                    title: {
                                        text: "Count of Item", 
                                        enabled: true,         
                                        fontSize: 10,     
                                        fontFamily: "Roboto",
                                    }
                                }
                            ],
                            series: [
                                {
                                    type: "line",
                                    xKey: "date",
                                    yKey: "Red",
                                    yName: "Red",
                                    
                                    marker:{
                                        fill:'red',
                                        size:2,
                                        shape:'square',
                                        stroke:"red"
                                    },
                                    stroke:'red'
                                    
                                },
                                {
                                    type: "line",
                                    xKey: "date",
                                    yKey: "Green",
                                    yName: "Green",
                                    marker:{
                                        fill:'green',
                                        size:2,
                                        shape:'square',
                                        stroke:'green'
                                    },
                                    stroke:'green'
                                },
                                {
                                    type: "line",
                                    xKey: "date",
                                    yKey: "Yellow",
                                    yName: "Yellow",
                                    marker:{
                                        fill:'#FFBF00',
                                        size:2,
                                        shape:'square',
                                        stroke:'#FFBF00'
                                    },
                                    stroke:'#FFBF00'
                                },
                                {
                                    type: "line",
                                    xKey: "date",
                                    yKey: "Black",
                                    yName: "Black",
                                    marker:{
                                        fill:'black',
                                        size:2,
                                        shape:'square',
                                        stroke:"black"
                                    },
                                    stroke:'black'
                                },
                                {
                                    type: "line",
                                    xKey: "date",
                                    yKey: "Blue",
                                    yName: "Blue",
                                    marker:{
                                        fill:'blue',
                                        size:2,
                                        shape:'square',
                                        stroke:"blue"
                                    },
                                    stroke:'blue'
                                },
                                {
                                    type: "line",
                                    xKey: "date",
                                    yKey: "White",
                                    yName: "White",
                                    marker:{
                                        fill:'gray',
                                        size:2,
                                        shape:'square',
                                        stroke:"gray"
                                    },
                                    stroke:'gray'
                                }
                            ],
                        legend:{
                            position:'top',
                            item:{
                                label:{
                                    fontSize:8,

                                },
                                marker:{
                                    size:10
                                },
                                line:{
                                    strokeWidth:1
                                }
                            }
                            
                        }
                        
                    }}/>
                    </ChartWrapper>
                    </AvailabilityTrendSection>
                    <AvailabilityTrendSection style={{border:'none'}}>
                    <ChartHeader>
                        <RadioGroup>
                            <ChartHeaderRadioGroup style={{gap:'2px'}} theme={themeUi}>
                                <input type="radio" value="parent" name="location" id="parent" defaultChecked onChange={()=>updateGraphState(2,'type',{label:"Parent",value:'Parent'})} style={{margin:0}}/>
                                <label htmlFor="parent" style={{fontSize:10}}>Parent</label>
                            </ChartHeaderRadioGroup>
                            <ChartHeaderRadioGroup style={{marginLeft:'10px',gap:'2px'}} theme={themeUi}>
                                <input type="radio" value="child" name="location" id="child" onChange={()=>updateGraphState(2,'type',{label:"Child",value:'Child'})} style={{margin:0}}/>
                                <label htmlFor="child"  style={{fontSize:10}}>Child</label>
                            </ChartHeaderRadioGroup>
                        </RadioGroup>

                        <CapsuleWrapper>
                            <VFCapsule
                                activeBtn={graphs[1].pen}
                                capsules={[
                                    {
                                        label:"On-Hand Inv.",
                                        value:'Tech'
                                    },
                                    {
                                        label:"Pipeline Inv.",
                                        value:'Eco'
                                    }
                                ]}
                                handleClick={(value:any)=>updateGraphState(2,'pen',value)}
                                
                            />
                        </CapsuleWrapper>
                    </ChartHeader>
                    <ChartWrapper>
                        <ExpandChartIcon src='/assets/img/VectorFLOW/BPR/expand-graph.svg' onClick={()=>toggleGraphModal(true,2)}/>
                        <AgCharts options={{
                            height:150,
                            width:300,
                            data:locationGraphData,
                            axes:[
                                {
                                    
                                    type:"category",
                                    position:'bottom',
                                    label:{
                                        fontSize:8
                                    }
                                },
                                {
                                    type:"number",
                                    position:'left',
                                    label:{
                                        fontSize:8
                                    }
                                },
                                {
                                    type: "number",
                                    position: 'left',
                                    label: {
                                        fontSize: 8
                                    },
                                    title: {
                                        text: "Count of Item", 
                                        enabled: true,         
                                        fontSize: 10,     
                                        fontFamily: "Roboto",
                                    }
                                }

                            ],
                            series: [
                                {
                                    type: "line",
                                    xKey: "date",
                                    yKey: "Red",
                                    yName: "Red",
                                    
                                    marker:{
                                        fill:'red',
                                        size:2,
                                        shape:'square',
                                        stroke:"red"
                                    },
                                    stroke:'red'
                                    
                                },
                                {
                                    type: "line",
                                    xKey: "date",
                                    yKey: "Green",
                                    yName: "Green",
                                    marker:{
                                        fill:'green',
                                        size:2,
                                        shape:'square',
                                        stroke:"green"
                                    },
                                    stroke:'green'
                                },
                                {
                                    type: "line",
                                    xKey: "date",
                                    yKey: "Yellow",
                                    yName: "Yellow",
                                    marker:{
                                        fill:'#FFBF00',
                                        size:2,
                                        shape:'square',
                                        stroke:"#FFBF00"
                                    },
                                    stroke:'#FFBF00'
                                },
                                {
                                    type: "line",
                                    xKey: "date",
                                    yKey: "Black",
                                    yName: "Black",
                                    marker:{
                                        fill:'black',
                                        size:2,
                                        shape:'square',
                                        stroke:"black"
                                    },
                                    stroke:'black',
                                    
                                },
                                {
                                    type: "line",
                                    xKey: "date",
                                    yKey: "Blue",
                                    yName: "Blue",
                                    marker:{
                                        fill:'blue',
                                        size:2,
                                        shape:'square',
                                        stroke:"blue"
                                    },
                                    stroke:'blue'
                                },
                                {
                                    type: "line",
                                    xKey: "date",
                                    yKey: "White",
                                    yName: "White",
                                    marker:{
                                        fill:'gray',
                                        size:2,
                                        shape:'square',
                                        stroke:"gray"
                                    },
                                    stroke:'gray'
                                }
                                ],
                                legend:{
                                    position:'top',
                                    item:{
                                        label:{
                                            fontSize:8,
        
                                        },
                                        marker:{
                                            size:10
                                        },
                                        line:{
                                            strokeWidth:1
                                        }
                                    }
                                    
                                }
                        }}/>
                    </ChartWrapper>
                    </AvailabilityTrendSection>
                    </React.Fragment>
                )}
            </AvailabilityTrendWrapper>
            }
            
           
             <ExpandedGraph
                onUpdateGraphs={updateGraphState}
                options={expandedGraphAllFilterValues}
                graphs={graphs}
                setGraphs={setGraphs}
                id={expandedGraphId}
                onTogglePen={(e)=>updateGraphState(expandedGraphId,"pen",e)}
                data={expandedGraphId===1?selfGraphData:locationGraphData}
                isOpen={isGraphOneOpen}
                onClose={()=>setIsGraphOneOpen(false)}
                horizon={horizon}
            />
           <div style={{display:'none'}}>                
                  <VFTable
                    ref={tempRef}
                    columnDefs={ResearchInsightsColumns}
                    rowData={exportExcelRowData}
                    {...tempAgGridProps}
                    maintainColumnOrder
                  />
                </div>
        </ResearchInsightsLayout>
        
        </GridStateContext.Provider>
    )
}

export default ResearchInsights