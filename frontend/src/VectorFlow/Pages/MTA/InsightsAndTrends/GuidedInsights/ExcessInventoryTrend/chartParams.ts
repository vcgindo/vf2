// export const chartParams1 = {
//     title:'Excess Inventory Trend (Count Of SKU)-Last 90 Days',
//     chartType:'line',
//     downloadName:'Excess Inventory Trend (Count Of SKU)-Last 90 Days',
//     LabelPosition:'bottom',
//     Labels:{
//         Xaxis:'Date',
//         Yaxis:'Count Of SKUs'
//     },
//     palette:{},
//     legend: {
//         enabled:true,
//         position: 'bottom',
//         item:{
//           marker:{
//             shape:'square'
//           }
//         }
//       },
//     chartKey:{
//         Xaxis:['date'],
//         Yaxis:[] // dynamic from backend
//     },
//     series:[  // Here Yaxis is dynamic
//         {
//             type: 'line',
//             xKey: 'date',
//             yKey: 'countSku',
//             strokeWidth: 3,
//         }
//     ],
//     // defaultColForChart:{}, not required as we are not showing grid data 
//     graphInfo: [
//         'This graph highlights the date-wise trend of excess inventory (On Hand) across various locations and products over the past 7 days','Excess Inventory = Quantity > Norm'
//    ],
//     customizedStyles:{
//         headerZoom:0.7, // default zoom is 1 
//         headerContainerHeight:'30px', // default height is 60px
//         agChartHeight:'86%'
//     }
// }



// export const chartParams2 = {
//     title: `Top 10 Products with Excess Inventory: In Value (${process.env.REACT_APP_CURRENCY || 'Rupee'}  Lakhs)`,
//     chartType:'line',
//     downloadName:`Top 10 Products with Excess Inventory: In Value (${process.env.REACT_APP_CURRENCY || 'Rupee'} Lakhs)`,
//     LabelPosition:'bottom',
//     Labels:{
//         Xaxis:'Date',
//         Yaxis:'Value In Lakhs'
//     },
//     palette:{},
//     legend: {
//         enabled:true,
//         position: 'bottom',
//         item:{
//           marker:{
//             shape:'square'
//           }
//         }
//       },
//     chartKey:{
//         Xaxis:['date'],
//         Yaxis:[] // dynamic from backend
//     },
//     series:[  // Here Yaxis is dynamic
//         {
//             type: 'line',
//             xKey: 'date',
//             yKey: 'value',
//             strokeWidth: 3,
//         }
//     ],
//     // defaultColForChart:{}, not required as we are not showing grid data 
//     graphInfo: [
//          'This graph highlights the date-wise trend of excess inventory (On Hand) in value across various locations and products over the past 7 days','Excess Inventory = Quantity > Norm'
//     ],
//     customizedStyles:{
//         headerZoom:0.7, // default zoom is 1 
//         headerContainerHeight:'30px', // default height is 60px
//         agChartHeight:'86%'
//     }
// }

export const createChartParams = (type:any, currency = 'Rupee') => {

    const isValueType = type === 'value';


    const config = isValueType

        ? {

            title: `Top 10 Products with Excess Inventory: In Value (${currency} Lakhs)`,
            yAxisLabel: 'Value In Lakhs',
            yKey: 'value',
            graphInfo: [
                'This graph highlights the date-wise trend of excess inventory (On Hand) in value across various locations and products over the past 7 days',
                'Excess Inventory = Quantity > Norm'
            ]
          }

        : {
            title: 'Excess Inventory Trend (Count Of SKU)-Last 90 Days',
            yAxisLabel: 'Count Of SKUs',
            yKey: 'countSku',
            graphInfo: [
                'This graph highlights the date-wise trend of excess inventory (On Hand) across various locations and products over the past 7 days',
                'Excess Inventory = Quantity > Norm'
            ]
          };


    return {
        title: config.title,
        downloadName: config.title, 
        chartType: 'line',
        LabelPosition: 'bottom',
        Labels: {
            Xaxis: 'Date',
            Yaxis: config.yAxisLabel,
        },
        palette:{
            fills:["#333333","#666666","#808080","#a6a6a6","#cccccc","#d8d8d8",],
            strokes:[ "#ffffff","#ffffff","#ffffff","#ffffff","#ffffff","#ffffff",]
        },
        legend: {
            enabled: true,
            position: 'bottom',
            item: {
                marker: {
                    shape: 'square'
                }
            }
        },
        chartKey: {
            Xaxis: ['date'],
            Yaxis: []
        },
        series: [{
            type: 'line',
            xKey: 'date',
            yKey: config.yKey,
            strokeWidth: 3,
        }],
        graphInfo: config.graphInfo,
        customizedStyles: {
            headerZoom: 0.7,
            headerContainerHeight: '30px',
            agChartHeight: '86%'
        }
    };
};