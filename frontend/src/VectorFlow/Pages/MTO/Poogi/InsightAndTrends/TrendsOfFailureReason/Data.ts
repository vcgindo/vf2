import { ColDef } from "ag-grid-enterprise";

export function TooltipRenderer(props: any) {
    const { datum, xKey, labels } = props;
    return `
<div style="width: 250px">
<div class="ag-chart-tooltip-title" style="background-color: #6C696A; display: flex; justify-content: center; align-items: center">
    ${datum[xKey]}
</div>
<div class="ag-chart-tooltip-content" style="color: white; background-color: #6C696A">

<div>
    ${labels?.map((label: any) => `
    <div style="display: flex;">
        <div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: ${label?.color}"></div>
        <div style="display:flex ;width: 100%; justify-content: space-between">
            <div style="width: 150px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" >${label.text}</div>
            <div>${datum[label?.key] || '--' }</div>
        </div>
    </div>
    `).join('')}
</div>
</div>
`
}

export function createSeriesData(labels: any) {
    const seriesData: any = [];
    for (let i = 0; i < labels.length; i++) {
        seriesData.push({
            type: "line",
            xKey: "month",
            yKey: labels[i].key,
            yName: labels[i].text,
            fill: labels[i].color,
            stroke:
                labels[i].color
            ,
            marker: {
                fill: labels[i].color,
                stroke: labels[i].color,
            },

            strokeWidth: 2,
            stacked: true,
            tooltip: {
                renderer: (params: any) => TooltipRenderer({...params, labels}),
            },
        });
    }


    return seriesData;
}

export const getMyColumnDefinitions = (labels: any): ColDef[] => {

    const labelKeys = labels.map((label: any) => label.key);

    const columns: ColDef[] = [
        ...labelKeys.map((key: any) => ({
            headerName: key,
            field: key,
            sortable: true,
            filter: true,
            width: 100,

        })),
    ];

    return columns;
};