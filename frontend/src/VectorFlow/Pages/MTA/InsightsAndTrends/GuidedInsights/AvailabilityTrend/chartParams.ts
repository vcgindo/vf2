export const chartParams1 = {
    title:'Availabilty Trend',
    chartType:'line',
    downloadName:'Availabilty Trend',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'Date',
        Yaxis:'Availability %'
    },
    palette:{
        fills:[
          "#333333",
          "#666666",
          "#808080",
          "#a6a6a6",
          "#cccccc",
          "#d8d8d8",
          "#4d4d4d",
          "#e0e0e0",
          "#f2f2f2",
          "#1a1a1a",
        ],
        strokes:[ "#ffffff","#ffffff","#ffffff","#ffffff","#ffffff","#ffffff", "#ffffff", "#ffffff", "#ffffff", "#ffffff"]
    },
    legend: {
        enabled:true,
        position: 'bottom',
        item:{
          marker:{
            shape:'square'
          }
        }
      },
    chartKey:{
        Xaxis:['week'],
        Yaxis:[] // dynamic from backend
    },
    series:[  // Here Yaxis is dynamic
        {
            type: 'line',
            xKey: 'week',
            yKey: 'percentage',
            strokeWidth: 3,
        }
    ],
    // defaultColForChart:{}, not required as we are not showing grid data 
    graphInfo: [
        "This graph highlights day wise availabilty percentage (On Hand) across locations",
        "Availabilty Perecentage = (Total instances excluding black/Total instances)*100",    ],
    customizedStyles:{
        headerZoom:0.7, // default zoom is 1 
        headerContainerHeight:'30px', // default height is 60px
        agChartHeight:'86%'
    }
}