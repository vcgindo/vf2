import { ColDef } from "ag-grid-enterprise";

export function TooltipRenderer({ datum, xKey }: any) {
    return `
<div style="width: 180px">
<div class="ag-chart-tooltip-title" style="background-color: #6C696A; display: flex; justify-content: center; align-items: center">
    ${datum[xKey]}
</div>
<div class="ag-chart-tooltip-content" style="color: white; background-color: #6C696A">

<div>
    <div style="display: flex;">
        <div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #F4BD8E">
        </div>
        <div style="display:flex ; width: 100%; justify-content: space-between">
            <div>1-2 days
            </div>
            <div> ${datum['1_2_d']}
            </div>
        </div>
    </div>
    <div style="display: flex;"><div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #F09241"></div><div style="display:flex ;width: 100%; justify-content: space-between"><div>3-7 days</div><div>${datum["3_7_d"]}</div></div></div>
    <div style="display: flex;"><div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #AD5000"></div><div style="display:flex ;width: 100%; justify-content: space-between"><div>8-15 days</div><div>${datum["8_15_d"]}</div></div></div>
    <div style="display: flex;"><div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #6A3001"></div><div style="display:flex ;width: 100%; justify-content: space-between"><div>16-30 days</div><div> ${datum["16_30_d"]}</div></div></div>
</div>
</div>
`
}
export function TooltipRendererIF({ datum, xKey }: any) {
    return `
<div style="width: 180px">
<div class="ag-chart-tooltip-title" style="background-color: #6C696A; display: flex; justify-content: center; align-items: center">
    ${datum[xKey]}
</div>
<div class="ag-chart-tooltip-content" style="color: white; background-color: #6C696A">

<div>
    <div style="display: flex;">
        <div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #F4BD8E">
        </div>
        <div style="display:flex ; width: 100%; justify-content: space-between">
            <div>0%-20%
            </div>
            <div> ${datum['0_2_p']}
            </div>
        </div>
    </div>
    <div style="display: flex;"><div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #F09241"></div><div style="display:flex ;width: 100%; justify-content: space-between"><div>20%-40%</div><div>${datum["20_40_p"]}</div></div></div>
    <div style="display: flex;"><div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #AD5000"></div><div style="display:flex ;width: 100%; justify-content: space-between"><div>40%-60%</div><div>${datum["40_60_p"]}</div></div></div>
    <div style="display: flex;"><div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #6A3001"></div><div style="display:flex ;width: 100%; justify-content: space-between"><div>60%-80%</div><div> ${datum["60_80_p"]}</div></div></div>
    <div style="display: flex;"><div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #6A3001"></div><div style="display:flex ;width: 100%; justify-content: space-between"><div>80%-100%</div><div> ${datum["80_100_p"]}</div></div></div>
</div>
</div>
`
}

export function createSeriesDataIF() {
    const seriesData: any = [];
    const labels = [
        { text: "0%-20%", color: "#F5B279", key: "0_2_p" },
        { text: "20%-40%", color: "#F09241", key: "20_40_p" },
        { text: "40%-60%", color: "#E36A00", key: "40_60_p" },
        { text: "60%-80%", color: "#AD5000", key: "60_80_p" },
        { text: "80%-100%", color: "#6A3000", key: "80_100_p" }
    ];

    for (let i = 0; i < labels.length; i++) {
        seriesData.push({
            type: "bar",
            xKey: "m",
            yKey: labels[i].key,
            yName: labels[i].text,
            strokeOpacity: 0,
            fill: labels[i].color,
            strokeWidth: 0.5,
            stacked: true,
            tooltip: {
                renderer: TooltipRendererIF,
            },
        });
    }

    return seriesData;
}
export function createSeriesData() {
    const seriesData: any = [];
    const labels = [
        { text: "1-2 days", color: "#F5B279", key: "1_2_d" },
        { text: "3-7 days", color: "#F09241", key: "3_7_d" },
        { text: "8-15 days", color: "#E36A00", key: "8_15_d" },
        { text: "16-30 days", color: "#AD5000", key: "16_30_d" },
    ];

    for (let i = 0; i < labels.length; i++) {
        seriesData.push({
            type: "bar",
            xKey: "m",
            yKey: labels[i].key,
            yName: labels[i].text,
            strokeOpacity: 0,
            fill: labels[i].color,
            strokeWidth: 0.5,
            stacked: true,
            tooltip: {
                renderer: TooltipRenderer,
            },
        });
    }

    return seriesData;
}

export const getMyColumnDefinitions = (labels: any): ColDef[] => {

    const columns: ColDef[] = [
        {
            headerName: 'Week',
            field: 'm',
            sortable: true,
            filter: true,
            width: 150,
        },
        ...labels.map((entry: any) => ({
            headerName: entry.text,
            field: entry.key,
            sortable: true,
            filter: true,
            width: 100,

        })),
    ];

    return columns;
};