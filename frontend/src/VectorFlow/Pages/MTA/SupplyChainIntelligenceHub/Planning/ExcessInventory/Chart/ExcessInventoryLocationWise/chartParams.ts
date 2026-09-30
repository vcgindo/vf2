// export const chartParams1 = {
//     title:'Top 10 Locations With Excess Inventory: Count Of SKUs',
//     chartType:'column',
//     downloadName:'Top-10 Loc With Excess Inv- Count of SKUs',
//     LabelPosition:'bottom',
//     Labels:{
//         Xaxis:'Location Name',
//         Yaxis:'Count Of SKUs'
//     },
//     palette:{
//         fills: ['#848484'],
//         strokes: ['#ffffff', '#ffffff'],
//     },
//     chartKey:{
//         Xaxis:['WHDescription'],
//         Yaxis:['SKUCounts']
//     },
//     series:[
//         {
//             type:'bar',
//             xKey:'WHDescription',
//             yKey:'SKUCounts',
//             yName:'Count of SKUs',
//             stacked:false,
//             barPadding:0.2,
            
//         }
//     ],
//     defaultColForChart:{
//         columns:['WHDescription','SKUCounts'],
//         start:0,
//         end:9
//     },
//     graphInfo:[
//         'This graph highlights the top 10 locations with the highest excess inventory (On Hand), measured in terms of the count of SKUs'
//     ]
// }


// export const chartParams2 = {
//     title:`Top 10 Locations with Excess Inventory: In Value (${process.env.REACT_APP_CURRENCY || 'Rupee'} Lakhs)`,
//     chartType:'column',
//     downloadName:'Top-10 Loc With Excess Inv- In Value',
//     LabelPosition:'bottom',
//     Labels:{
//         Xaxis:'Location Name',
//         Yaxis:'Value In Lakhs'   
//     },
//     palette:{
//         fills: ['#848484'],
//         strokes: ['#ffffff', '#ffffff'],
//     },
//     chartKey:{
//         Xaxis:['WHDescription'],
//         Yaxis:['SumOfAmount']
//     },
//     series:[
//         {
//             type:'bar',
//             xKey:'WHDescription',
//             yKey:'SumOfAmount',
//             yName:'Value In Lakhs',
//             stacked:false,
//             barPadding:0.2,
            
//         }
//     ],
//     defaultColForChart:{
//         columns:['WHDescription','SumOfAmount'],
//         start:0,
//         end:9
//     },
//     graphInfo:[
//         'This graph highlights the top 10 locations with the highest excess inventory (On Hand), assessed in terms of monetary value.'
//     ]
// }


export const createChartParams = (type: any, currency: any) => {

    const isSku = type === 'sku';


    const yKey = isSku ? 'SKUCounts' : 'SumOfAmount';
    const yAxisLabel = isSku ? 'Count Of SKUs' : 'Value In Lakhs';
    const yName = isSku ? 'Count of SKUs' : 'Value In Lakhs';
    
    const title = isSku
        ? 'Top 10 Locations With Excess Inventory: Count Of SKUs'
        : `Top 10 Locations with Excess Inventory: In Value (${currency} Lakhs)`;

    const downloadName = isSku
        ? 'Top-10 Loc With Excess Inv- Count of SKUs'
        : 'Top-10 Loc With Excess Inv- In Value';

    const graphInfo = [
        isSku
            ? 'This graph highlights the top 10 locations with the highest excess inventory (On Hand), measured in terms of the count of SKUs.'
            : 'This graph highlights the top 10 locations with the highest excess inventory (On Hand), assessed in terms of monetary value.'
    ];


    return {
        title,
        downloadName,
        chartType: 'column',
        LabelPosition: 'bottom',
        Labels: {
            Xaxis: 'Location Name',
            Yaxis: yAxisLabel,
        },
        palette: {
            fills: ['#848484'],
            strokes: ['#ffffff', '#ffffff'],
        },
        chartKey: {
            Xaxis: ['WHDescription'],
            Yaxis: [yKey], // Dynamic Y-axis key
        },
        series: [{
            type: 'bar',
            xKey: 'WHDescription',
            yKey: yKey, // Dynamic yKey
            yName: yName, // Dynamic yName
            stacked: false,
            barPadding: 0.2,
        }],
        defaultColForChart: {
            columns: ['WHDescription', yKey], // Dynamic columns
            start: 0,
            end: 9,
        },
        graphInfo,
    };
};