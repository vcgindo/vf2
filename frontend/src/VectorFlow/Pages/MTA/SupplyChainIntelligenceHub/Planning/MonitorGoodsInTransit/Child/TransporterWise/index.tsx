import { useRef, useMemo } from "react";
import { Allotment } from 'allotment';
import "allotment/dist/style.css";
import VFTable from "../../../../../../../../components/VectorFLOW/commons/VFTable";
import { type GridRef } from "../../../../../../../types/MDM";
import { ColDef } from "ag-grid-enterprise";
import {SCChartHeaderContainer, SCChartHeader, SCChartContainer, SCHorizontalDivider} from '../../styles';
import VFInfoTip from "../../../../../../../../components/VectorFLOW/commons/VFInfoTip";


interface MonitorGITChildTransporterWiseProps{
    data:any
}


const MonitorGITChildTransporterWise = ({data}:MonitorGITChildTransporterWiseProps) => {

    const refGraph1 = useRef<GridRef>();
    const refGraph2 = useRef<GridRef>(); 

    const coldefs:ColDef[] = [
        {
            field:'tn',
            headerName:'Transporter Name',
            colId:'tn'
        },
        {
            field:'d',
            headerName:'Delay',
            colId:'d'
        },
        {
            field:'spd',
            headerName:'Super Delay',
            colId:'spd'
        }
    ]

    const generateChart = () => {
        const container1 = document.getElementById('TransporterWiseGraph1') as HTMLElement
        refGraph1.current?.api.createRangeChart({
          chartType:'stackedColumn',
          cellRange: {
            columns: ['tn', 'spd', 'd'],
            rowStartIndex:0,
            rowEndIndex:9
          },
          chartContainer:container1
        })

        // const container2 = document.getElementById('LocationWiseGraph2') as HTMLElement
        // refGraph2.current?.api.createRangeChart({
        //   chartType:'stackedColumn',
        //   cellRange: {
        //     columns: ['ln', 'spd', 'd'],
        //     rowStartIndex:0,
        //     rowEndIndex:9
        //   },
        //   chartContainer:container2
        // })
      }

      const getChartToolbarItems:any = () => ['chartDownload'];

      const chartThemeOverrides = useMemo<any>(() => { 
        return {
            palette:{
                fills:['#0c7528','#570dbf']
            },
              common: {
                  legend:{
                    position:'top'
                  },
                  axes:{
                    category:{
                        title:{
                            enabled:true,
                            text:'Transporter Name',
                            position:'bottom',

                        }
                    },
                    number:{
                        title:{
                            enabled:true,
                            text:"Count of LRs",
                            position:"left"
                        }
                      }
                  },
                  
              },
          };
      }, []);

      const myCustomTheme:any = {
        palette: {
            fills: ['#9A0101', '#F02424'],
            strokes: ['#ffffff', '#ffffff'],
          },
      }

      const graph1 = [
        'The graph illustrates the top 10 transporters having the maximum no. of LRs with SKUs in On-Hand Black/Red (shortage of on-handinventory) experiencing high transport ageing (Transportation Time > Standard Lead Time)',
        'Care needs to be taken to reduce the transportation time of LRs corresponding to above transporters',
        'Super Delay : Transportation Lead Time >= 1.5 x Standard Lead Time',
        'Delay : Transportation Lead Time > Standard Lead Time'
      ]

      const graph2 = [
        'This box plot graph displays the statistical distribution of delay days in transport for various transporters. Each box represents the range of delayed LRs as on today'
      ]
    
    
    return(
        <>
            <Allotment>
                <Allotment.Pane preferredSize={1000}>
                    <SCChartContainer height={"547px"}>
                        <SCChartHeaderContainer>
                            <SCChartHeader>Top 10 Transporters: Max LRs With On-Hand Black/Red SKUs Along With High Transport Ageing</SCChartHeader>
                        </SCChartHeaderContainer>
                        <SCHorizontalDivider/>
                        <div style={{display:'none'}}>
                            <VFTable
                                ref={refGraph1}
                                columnDefs={coldefs}
                                rowData={data['maxTechBlackRedColumn']}
                                enableCharts={true}
                                enableRangeSelection={true}
                                onGridReady={generateChart}
                                getChartToolbarItems={getChartToolbarItems}
                                chartToolPanelsDef={
                                    {
                                        panels:[]
                                    }
                                }
                                chartThemeOverrides={chartThemeOverrides}
                                chartThemes={['myCustomTheme']}
                                customChartThemes={{
                                    'myCustomTheme':myCustomTheme
                                }}
                            />
                        </div>
                        <div id="TransporterWiseGraph1"></div>
                    </SCChartContainer>
                    <div style={{marginLeft:'10px',marginRight:'10px'}}>
                        <VFInfoTip text={graph1}/>
                    </div>
                </Allotment.Pane>
                <Allotment.Pane>
                    <SCChartContainer height={'547px'}>
                            <SCChartHeaderContainer>
                                <SCChartHeader>Statistical Overview of Delay Days in Transport at Receiving Locations</SCChartHeader>
                            </SCChartHeaderContainer>
                            <SCHorizontalDivider/>
                            <div style={{display:'none'}}>
                                <VFTable
                                    ref={refGraph2}
                                    columnDefs={coldefs}
                                    rowData={data['delayDaysStatisticalBox']}
                                    enableCharts={true}
                                    enableRangeSelection={true}
                                    // onGridReady={generateChart}
                                    getChartToolbarItems={getChartToolbarItems}
                                    chartToolPanelsDef={
                                        {
                                            panels:[]
                                        }
                                    }
                                    chartThemeOverrides={chartThemeOverrides}
                                    chartThemes={['myCustomTheme']}
                                    customChartThemes={{
                                        'myCustomTheme':myCustomTheme
                                    }}
                                />
                            </div>
                            <div id="TransporterWiseGraph2"></div>
                    </SCChartContainer>
                    <div style={{marginLeft:'10px',marginRight:'10px'}}>
                        <VFInfoTip text={graph2}/>
                    </div>
                </Allotment.Pane>
            </Allotment>
        </>
    )
    
}

export default MonitorGITChildTransporterWise;