import { Allotment } from 'allotment'
import _ from 'lodash'
import { useEffect, useState } from 'react'
import { FilterPageName, UIGridCode } from '../../../../../../VectorFlow/Pages/MTO/Common/Enum'
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from '../../../../../../VectorFlow/Services/MTO/Common/UserUIConfig'
import { useGetElapsedDaysforDeptPlantData, useGetElapsedTimeData, useGetElapsedTimeDataForExcelExport } from '../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/ElapseTime'
import MTOActionToolBar from '../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar'
import { useUserData } from "../../../../../../context/index"
import { notifyError, notifySuccess } from '../../../../../../helpers/notify'
import OverlayLoader from '../../../Common/Loader'
import { BTRAllomentSection, BTRTableWrapper, HorizontalViewWrapper } from '../../../Common/SplitGraphContainer/styles'
import TagCellToolTip from '../../../Poogi/InsightAndTrends/OTIFAnalysis/TagCellRenderer/TagCellRenderer'
import DeptWiseGraph from './DeptWiseGraph'
import WeekWiseGraph from './WeekWiseGraph'




import { GridOptions } from 'ag-grid-enterprise'
import CommonGridview from '../../../../../../helpers/CommonGridview'
import BPPRenderer from '../../../Common/BPRRenderer/BPPRenderer'
import CustomTagTooltip from '../../../Poogi/InsightAndTrends/OTIFAnalysis/CustomTagTooltip'
import { SCDynamicContainer } from './GridView/styles'

const ElapsedTime = () => {

    const [isGridView, setIsGridView] = useState(false);
    const [deptwiseChartTableData, setDeptwiseChartTableData] = useState([]);
    const [deptwiseChartData, setDeptwiseChartData] = useState([]);
    const [alertData, setAlertData] = useState([]);
    const [weeklyChartTableData, setWeeklyChartTableData] = useState([]);
    const [weeklyChartData, setWeeklyChartData] = useState([]);
    const [selectedPlant, setSelectedPlant] = useState<any>();
    const [selectedDept, setSelectedDept] = useState<any>();

    const { mutateAsync: getElapsedTimeData, isLoading } = useGetElapsedTimeData()
    const { mutateAsync: getElapsedDaysforDeptPlantData, isLoading: isLoading2 } = useGetElapsedDaysforDeptPlantData()
    const { isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
    const { isLoading: isGetUserConfig } = useGetUserUIConfigData();
    const { user } = useUserData();
    const reportName = "Elapse Time";


    const { mutateAsync: getElapsedTimeDataExcelExport , isLoading:gridDataLoading} = useGetElapsedTimeDataForExcelExport();  
    
    
    
    
    const themeUi = user?.user?.theme_ui

    const getDeptWiseChartData = async () => {
        try {
            const data = await getElapsedTimeData({ graphflag: 1 });
            const chartData: any = []
            const tableData: any = []
            const alertData: any = []
            Object.entries(data.data.data).forEach((entry: any) => {
                const obj = _.cloneDeep(entry[1]);
                if (obj.cl != "Grey") {
                    alertData.push({ x: entry[0], y: [obj.uw + 1] })
                } else {
                    alertData.push({ x: entry[0], y: [] })
                }
                delete obj["cl"]
                chartData.push({ x: entry[0], y: Object.values(obj).sort((a: any, b: any) => a - b) })
                tableData.push({ ...entry[1], department: entry[0] })
            })
            setDeptwiseChartTableData(tableData);
            setDeptwiseChartData(chartData)
            setAlertData(alertData)
            notifySuccess("Data Fetched Successfully!")
        }
        catch (err: any) {
            console.log(err)
            notifyError("Something Went Wrong")
        }

    }

    const getWeeklyChartData = async () => {
        try {
            const data = await getElapsedDaysforDeptPlantData({ plant: selectedPlant.value, dept: selectedDept.value });
            const chartData: any = []
            const tableData: any = []
            Object.entries(data.data.data).forEach((entry: any) => {
                const obj = _.cloneDeep(entry[1]);
                delete obj["cl"]
                chartData.push({ x: entry[0], y: Object.values(obj).sort((a: any, b: any) => a - b) })
                tableData.push({ ...entry[1], week: entry[0] })
            })
            setWeeklyChartTableData(tableData);
            setWeeklyChartData(chartData)
            setAlertData(alertData)
            notifySuccess("Data Fetched Successfully!")
        }
        catch (err: any) {
            console.log(err)
            notifyError("Something Went Wrong")
        }
    }
    
    const handleSelectionChange = (newPlant: any, newDept: any) => {
        setSelectedPlant(newPlant);
        setSelectedDept(newDept);
    }

    useEffect(() => {
        getDeptWiseChartData();
    }, [])

    useEffect(() => {
        if (selectedDept?.value && selectedPlant?.value) {
            getWeeklyChartData()
        }
    }, [selectedDept, selectedPlant])



    const colDefCustomizations = {
        'Tags': {
            tooltipValueGetter: (params: any) => params.value,
            cellRenderer: TagCellToolTip,
            cellStyle: {
                display: 'flex',
                justifyContent: "center",
            },
            minwidth:100
        },
        'BPP': {
            cellRenderer: BPPRenderer,
            minwidth:100
        },
    }


      const defaultColDef = {
            // suppressMenu: true,
            autoHeaderHeight: true,
            filter: "agTextColumnFilter",
            floatingFilter: true,
            enableRowGroup: true,
            floatingFilterComponentParams: { suppressFilterButton: true },
            tooltipComponent: CustomTagTooltip,
            initialWidth: 110,
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
    
        const gridOptions: GridOptions = {
            groupDefaultExpanded: 0,
            detailRowHeight: 500,
            rowHeight: 26,
            rowGroupPanelShow: 'always',
            getRowStyle: (params: any) => {
                return {
                    background: params.node.rowIndex % 2 === 0 ? "#F4F4F4" : "#FFFFFF",
                };
            },
            defaultColDef,
        };

    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        {(isLoading || isLoading2 || isUpdateUserConfig || isGetUserConfig) && (
          <OverlayLoader />
        )}
        {!isGridView && (
          <MTOActionToolBar
            comp={"BTRMTO"}
            themeUi={themeUi}
            isChartGridToggle
            isExcelExport={isGridView}
            setIsGridView={setIsGridView}
            isGridView={isGridView}
           
          />
        )}
        <HorizontalViewWrapper style={{ flex: 1 }}>
          {isGridView ? (
           
            <CommonGridview
              columnDefinationProps={{
                customColDef: colDefCustomizations,
              }}
              gridDataLoading={gridDataLoading}
              reportName={reportName}
              customGridOptions={gridOptions}
              excelExportParams={{
                isExcelExportFromBackend: true,
                excelExportReportName: FilterPageName.Poogi_Elapsed_Time,
                excelExportSheetName: FilterPageName.Poogi_Elapsed_Time,
              }}
              reportNameId={UIGridCode.ProdElapsedTime}
              getExcelExportData={getElapsedTimeDataExcelExport}
              getRowData={getElapsedTimeData}
              actionToolBarProps={{
                comp: "BTRMTO",
                isAddFilterButton: false,
                isChartGridToggle: true,
                isGridView: isGridView,
                setIsGridView: setIsGridView,
              }}
              VFWrapper={SCDynamicContainer}
            />
          ) : (
            
              <BTRTableWrapper style={{ height:"95%", paddingLeft: "20px" }}>
                <Allotment vertical={false} separator={false}>
                  <Allotment.Pane
                    minSize={400}
                    preferredSize={"50%"}
                    className="allotment-pane-custom"
                  >
                    <BTRAllomentSection>
                      <DeptWiseGraph
                        chartData={deptwiseChartData}
                        chartTableData={deptwiseChartTableData}
                        alertData={alertData}
                      />
                    </BTRAllomentSection>
                  </Allotment.Pane>
                  <Allotment.Pane
                    minSize={400}
                    preferredSize={"50%"}
                    className="allotment-pane-custom"
                  >
                    <BTRAllomentSection>
                      <WeekWiseGraph
                        handleSelectionChange={handleSelectionChange}
                        chartTableData={weeklyChartTableData}
                        chartData={weeklyChartData}
                        plant={selectedPlant}
                        dept={selectedDept}
                      />
                    </BTRAllomentSection>
                  </Allotment.Pane>
                </Allotment>
              </BTRTableWrapper>
            
          )}
        </HorizontalViewWrapper>
      </div>
    );
}

export default ElapsedTime