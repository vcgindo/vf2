export const chartParams1 = {
    title:'Trend Of #SKU-Locations With Continuous Black/Red/White Status >= Selected Minimum Ageing',
    chartType:'line',
    downloadName:'Excess Inventory Trend (Count Of SKU)-Last 90 Days',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'Date',
        Yaxis:'No Of SKU-Locations'
    },
    palette:{
        fills: ['#DA3535', '#000000', '#BFBFBF'],
        strokes: ['#ffffff', '#ffffff', '#ffffff'],
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
        Xaxis:['date'],
        Yaxis:[] // dynamic from backend
    },
    series: [
        {
          type: "line" as const,
          xKey: "date",
          yKey: "red",
          yName: "red",
          stroke: "#DA3535",
          marker: {
            fill: "red",
            stroke: "red",
            size: 8,
          },
        },
        {
          type: "line" as const,
          xKey: "date",
          yKey: "black",
          yName: "black",
          strokeWidth: 3,
          stroke: "#000000",
          marker: {
            fill: "black",
            stroke: "black",
            size: 8,
          },
        },
        {
          type: "line" as const,
          xKey: "date",
          yKey: "white",
          yName: "white",
          strokeWidth: 3,
          stroke: "#BFBFBF",
          marker: {
            fill: "grey",
            stroke: "grey",
            size: 8,
          },
        },
      ],
    // defaultColForChart:{}, not required as we are not showing grid data 
    graphInfo: [
        "This graph highlights the trends of #SKU-Location with continous (On Hand) black,red or white status, each greater than or equal to the selected mimimum agening",
    ],
    customizedStyles:{
        headerZoom:0.7, // default zoom is 1 
        headerContainerHeight:'30px', // default height is 60px
        agChartHeight:'86%'
    }
}