import moment from 'moment'
import { useState } from 'react'
import SplitGraphContainer from '../../../../../../../VectorFlow/Pages/MTO/Common/SplitGraphContainer'
import VFInfoToolTip from '../../../../../../../components/VectorFLOW/commons/VFInfoToolTip'
import { SCChartHeaderContainer, SCChartMainContainer } from '../../../../../../../VectorFlow/Pages/MTO/Common/SplitGraphContainer/styles'
import { createSeriesData, getMyColumnDefinitions, TooltipRenderer } from '../Data'
import { AgChartOptions } from 'ag-charts-community'
import { useGetDate } from '../../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/RMPMExpediting'

interface OTFailedGraphProps {
    OTFailedData: any,
}

const OTFailedGraph = (props: OTFailedGraphProps) => {

    const { OTFailedData } = props;

    const graph1 = ['This Graph highlights the extent of delays experienced by OT Failed completed orders.']

    const [hideChart1, toggleChart1] = useState(false);
    const [tableLoading, setTableLoading] = useState(false);
    const [chartLoading, setChartLoading] = useState(false);
    const { data: apiResponseData } = useGetDate();

    const generateHeader = () => {
        return (
            <>
                <SCChartMainContainer style={{ zoom: 1, width: '100%' }}>
                    <div
                        data-testid="otif-graph"
                        style={{
                            fontSize: "12px",
                            margin: "auto auto",
                            fontFamily: "Roboto",

                            textAlign: "center",
                        }}
                    >
                        <span style={{ fontWeight: 500 }}>Extent Of Delay For OT Failed Orders &nbsp;</span>
                        <span style={{ fontWeight: 350 }}>{`(${moment(apiResponseData?.data?.data || '-').subtract(90, 'days').format('D MMM YYYY')} - ${moment(apiResponseData?.data?.data || '-').format('D MMM YYYY')})`}</span>
                    </div>

                    <SCChartHeaderContainer>

                        <div style={{ marginLeft: 30, marginBottom: '-5px' }}>
                            <VFInfoToolTip infoList={graph1} />
                        </div>
                        <div onClick={() => { toggleChart1(!hideChart1) }} style={{ marginLeft: 10, marginBottom: '-5px', marginRight: '10px' }}>
                            <img src='/assets/img/VectorFLOW/BPR/minimize.svg' height={13} width={13} color={"#CCCCCC"} />
                        </div>
                    </SCChartHeaderContainer>
                </SCChartMainContainer>
            </>

        )
    }

    const labels = [
        { text: "1-2 days", color: "#F5B279", key: "1_2_d" },
        { text: "3-7 days", color: "#F09241", key: "3_7_d" },
        { text: "8-15 days", color: "#E36A00", key: "8_15_d" },
        { text: "16-30 days", color: "#AD5000", key: "16_30_d" },
    ];

    const colDef: any = getMyColumnDefinitions(labels);

    const options: AgChartOptions = {
        series: createSeriesData(),
        data: OTFailedData?.data || [],
        axes: [
            {
                type: "category",
                position: "bottom",
                label: {
                    fontSize: 7,
                    fontWeight: "bold",
                    color: "black",
                },
                gridLine: {
                    enabled: false,
                },
            },
            {
                title: {
                    text: "Count Of Orders",
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
                },
                gridLine: {
                    enabled: false,
                },
            },

        ],

        legend: {
            item: {
                label: {
                    fontSize: 10
                },
            },
        },

    }

    return (
        <div style={{ height: "100%", paddingBottom: '20px', display: 'flex', justifyContent: 'left', marginRight: '7px' }}>
            <SplitGraphContainer
                tableLoading={tableLoading}
                chartLoading={chartLoading}
                setTableLoading={setTableLoading}
                setChartLoading={setChartLoading}
                data={OTFailedData?.data || []}
                rowData={OTFailedData?.data || []}
                graphTitle={``}
                tableTitle={``}
                options={options}
                colDef={colDef}
                header={generateHeader}
                hideChart={hideChart1}
                toggleChart={toggleChart1}
                TooltipRenderer={TooltipRenderer}
                graphType={11}
            />

        </div>
    )
}

export default OTFailedGraph