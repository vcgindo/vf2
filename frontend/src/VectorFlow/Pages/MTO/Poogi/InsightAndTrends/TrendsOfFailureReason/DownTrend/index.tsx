import moment from 'moment'
import React, { useEffect, useState } from 'react'
import SplitGraphContainer from '../../../../../../../VectorFlow/Pages/MTO/Common/SplitGraphContainer'
import VFInfoToolTip from '../../../../../../../components/VectorFLOW/commons/VFInfoToolTip'
import { SCChartHeaderContainer, SCChartMainContainer } from '../../../../../../../VectorFlow/Pages/MTO/Common/SplitGraphContainer/styles'
import { useGetDate } from '../../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/RMPMExpediting'
import { AgChartOptions } from 'ag-charts-community'
import { createSeriesData, getMyColumnDefinitions, TooltipRenderer } from '../Data'

const DownTrend = (props: any) => {
    const {graphData} = props;
    const [hideChart1, toggleChart1] = useState(false);    
    const [tableLoading, setTableLoading] = useState(false);
    const [chartLoading, setChartLoading] = useState(false);
    const [graphColDef, setGraphColDef] = useState<any>([]);
    const [rawData, setRawData] = useState<any>([]);
    const [labelData, setLabelData] = useState<any>([]);
    const { data: apiResponseData, /*isLoading, refetch*/ } = useGetDate();

    const infoTipData = ['This graph highlights the failure reasons that have experienced decrease in occurrence by more than 15% from the average of last 3 months.']
    
    const generateHeader = () => {
        return (
            <>
                <SCChartMainContainer style={{ zoom: 1, width: '100%' }}>
                    <div
                        data-testid="otif-graph"
                        style={{
                            fontSize: "10.5px",
                            margin: "auto auto",
                            padding: '0 4px',
                            fontFamily: "Roboto",

                            textAlign: "center",
                        }}
                    >
                        <span style={{ fontWeight: 500 }}>Major-Minor Reasons Impacting OTIF But Showing A Downward Trend &nbsp;</span>
                        <span style={{ fontWeight: 350 }}>{`(${moment(date).subtract(150, 'days').format('D MMM YYYY')} - ${moment(date).format('D MMM YYYY')})`}</span>
                    </div>
                    <SCChartHeaderContainer>

                        <div style={{ marginLeft: 30, marginBottom: '-5px' }}>
                            <VFInfoToolTip infoList={infoTipData} />
                        </div>
                        <div onClick={() => { toggleChart1(!hideChart1) }} style={{ marginLeft: 10, marginBottom: '-5px', marginRight: '10px' }}>
                            <img src='/assets/img/VectorFLOW/BPR/minimize.svg' height={13} width={13} color={"#CCCCCC"} />
                        </div>
                    </SCChartHeaderContainer>
                </SCChartMainContainer>
            </>

        )
    }

    const colDef: any = getMyColumnDefinitions(graphColDef);

    const date = apiResponseData?.data?.data;

    const checkLabel = (labels: any, key: string) => {
        for(let i = 0; i < labels.length; i++){
            if(key === labels[i]?.key){
                return true;
            }
        }
        return false;
    }

    useEffect(()=>{
        if(graphData){
            const months = Object.keys(graphData);
            const EUData: any = [];
            const labels: any = [];
            for(let i = 0; i < months.length; i++){
                const data: any = { month: months[i] };
                const reasons = graphData[months[i]];
                for(let j = 0; j < reasons?.length; j++){
                    const key = reasons[j].r
                    data[key] = reasons[j].oc;
                    if(!checkLabel(labels, key)){
                        labels.push({ text: key, color: reasons[j].clr, key: key })
                    }
                }
                EUData.push(data);
            }
            setRawData(EUData);
            setLabelData(labels);
            setGraphColDef( [...labels, { text: 'Month', color: '#418D18', key: 'month' }] );
        }
    },[graphData])

    const options: AgChartOptions = {
        series: createSeriesData(labelData),
        data: rawData,
        axes: [
            {
                type: "category",
                position: "bottom",
                label: {
                    fontSize: 7,
                    fontFamily: 'Roboto',
                    fontWeight: "bold",
                    color: "black",
                },
                gridLine: {
                    enabled: false,
                },
            },
            {
                title: {
                    text: "Number Of Orders Impacted",
                    fontFamily: "Roboto",
                    fontSize: 10,
                    fontWeight: 600,
                    fontStyle: 'normal',
                    spacing: 9
                },
                type: "number",
                line: { enabled: true },
                position: "left",
                label: {
                    fontSize: 8,
                    fontWeight: "bold",
                    color: "black",
                    fontFamily: 'Robot',
                },
                gridLine: {
                    enabled: false,
                },
            },

        ],

        legend: {
            item: {
                marker: {
                    shape: 'square',
                },
                label: {
                    fontSize: 10
                },
            },
        },

    }

    return (
        <div style={{ height: "100%", paddingBottom: '20px', display: 'flex', justifyContent: 'left', marginLeft: '10px' }}>
            <SplitGraphContainer
                tableLoading={tableLoading}
                chartLoading={chartLoading}
                setTableLoading={setTableLoading}
                setChartLoading={setChartLoading}
                data={rawData}
                rowData={rawData}
                graphTitle={``}
                tableTitle={``}
                options={options}
                colDef={colDef}
                header={generateHeader}
                hideChart={hideChart1}
                toggleChart={toggleChart1}
                TooltipRenderer={TooltipRenderer}
                graphType={12}
                columnsData={graphColDef}
                downloadFileName={'Major-Minor Reasons Impacting OTIF But Showing A Downward Trend'}
            />
        </div>
    )
}

export default DownTrend