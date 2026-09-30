// export const chartParams1 = {
//     title:'Top 10 Products with Excess Inventory: Number Of Locations',
//     chartType:'column',
//     downloadName:'Top-10 Prd With Excess Inv- No of Loc',
//     LabelPosition:'bottom',
//     Labels:{
//         Xaxis:'Product Name',
//         Yaxis:'Count Of Locations'   
//     },
//     palette:{
//         fills: ['#848484'],
//         strokes: ['#ffffff', '#ffffff'],
//     },
//     chartKey:{
//         Xaxis:['SKUDescription'],
//         Yaxis:['WHCount']
//     },
//     series:[
//         {
//             type:'bar',
//             xKey:'SKUDescription',
//             yKey:'WHCount',
//             yName:'Count of Locations',
//             stacked:false,
//             barPadding:0.2,
//         }
//     ],
//     defaultColForChart:{
//         columns:['SKUDescription','WHCount'],
//         start:0,
//         end:9
//     },
//     graphInfo:[
//         'This graph highlights the top 10 products with surplus inventory (On Hand), in maximum number of locations',
//     ]
// }


// export const chartParams2 = {
//     title:`Top 10 Products with Excess Inventory: In Value (${process.env.REACT_APP_CURRENCY || 'Rupee'} Lakhs)`,
//     chartType:'column',
//     downloadName:'Top-10 Prd With Excess Inv- In Value',
//     LabelPosition:'bottom',
//     Labels:{
//         Xaxis:'Product Name',
//         Yaxis:'Value In Lakhs'   
//     },
//     palette:{
//         fills: ['#848484'],
//         strokes: ['#ffffff', '#ffffff'],
//     },
//     chartKey:{
//         Xaxis:['SKUDescription'],
//         Yaxis:['SumAmount']
//     },
//     series:[
//         {
//             type:'bar',
//             xKey:'SKUDescription',
//             yKey:'SumAmount',
//             yName:'Value In Lakhs',
//             stacked:false,
//             barPadding:0.2,
//         }
//     ],
//     defaultColForChart:{
//         columns:['SKUDescription','SumAmount'],
//         start:0,
//         end:9
//     },
//     graphInfo:[
//         'This graph highlights the top 10 products with the highest excess inventory (On Hand), assessed in terms of monetary value.'
//     ]
// }

export const createChartParams = (type:any, currency = 'Rupee') => {
    // Determine if the chart is for value or for location count
    const isValueType = type === 'value';

    // Define the parameters that change based on the type
    const yKey = isValueType ? 'SumAmount' : 'WHCount';
    const yAxisLabel = isValueType ? 'Value In Lakhs' : 'Count Of Locations';
    const yName = isValueType ? 'Value In Lakhs' : 'Count of Locations';

    const title = isValueType
        ? `Top 10 Products with Excess Inventory: In Value (${currency} Lakhs)`
        : 'Top 10 Products with Excess Inventory: Number Of Locations';

    const downloadName = isValueType
        ? 'Top-10 Prd With Excess Inv- In Value'
        : 'Top-10 Prd With Excess Inv- No of Loc';

    const graphInfo = [
        isValueType
            ? 'This graph highlights the top 10 products with the highest excess inventory (On Hand), assessed in terms of monetary value.'
            : 'This graph highlights the top 10 products with surplus inventory (On Hand), in maximum number of locations.'
    ];

    // Return the combined chart configuration object
    return {
        title,
        downloadName,
        chartType: 'column',
        LabelPosition: 'bottom',
        Labels: {
            Xaxis: 'Product Name',
            Yaxis: yAxisLabel,
        },
        palette: {
            fills: ['#848484'],
            strokes: ['#ffffff', '#ffffff'],
        },
        chartKey: {
            Xaxis: ['SKUDescription'],
            Yaxis: [yKey], // Dynamic Y-axis key
        },
        series: [{
            type: 'bar',
            xKey: 'SKUDescription',
            yKey: yKey, // Dynamic yKey
            yName: yName, // Dynamic yName
            stacked: false,
            barPadding: 0.2,
        }],
        defaultColForChart: {
            columns: ['SKUDescription', yKey], // Dynamic columns
            start: 0,
            end: 9,
        },
        graphInfo,
    };
};