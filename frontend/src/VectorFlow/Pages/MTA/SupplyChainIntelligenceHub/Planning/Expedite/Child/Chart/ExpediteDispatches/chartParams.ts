export const chartParams1 = {
    title:'Top 10 Receiving Locations: Max Pipeline Inv. Black/Red SKUs With Rationed Quantity Available At Parent',
    chartType:'stackedColumn',
    downloadName:'Top 10 Receiving Loc- (Max Pipeline Inv B/R Available at parent)',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'Parent Location Name',
        Yaxis:'Count Of SKUs'
    },
    palette:{
        fills: ["#D0A928"],
        strokes: ["#ffffff", "#ffffff"],
    },
    legend:{
        enabled:true,
        position:'bottom'
    },
    chartKey:{
        Xaxis:['WHDescription'],
        Yaxis:[] // dynamic from backend
    },
    series:[  // Here Yaxis is dynamic
        {
            type:'bar',
            xKey:'WHDescription',  
            stacked:true,  
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'WHDescription',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'WHDescription',
            stacked:true,
            barPadding:0.2,
        }
    ],
    defaultColForChart:{}, // dynamic from backend
    graphInfo: [
        "This graph highlights the top 10 receiving locations with maximum SKUs in Pipeline Black/Red which have rationed quantity available at parent location.",
        "To improve availability, expedite dispatches to these locations.",
   ],
    customizedStyles:{
        headerZoom:0.7, // default zoom is 1 
        headerContainerHeight:'30px', // default height is 60px
        agChartHeight:'86%'
    }
}


export const chartParams2 = {
    title:'Comparision of Availability- Pre Rationing vs Post Rationing',
    chartType:'pie',
    downloadName:'Comparision of Availability- Pre vs Post',
    palette:{
        fills: ['#F02424','#E3812D','#418D18'],
        strokes: ['#ffffff', '#ffffff'],
    },
    series: [
        {
          type: "pie",
          title: {
            text: "PRE",
          },
          fills: ["#fff","#000000","#ED1C24","#FFCB05", "#418D18", "#BCBCBC","#355FD3"],
          angleKey: "pre",
          sectorLabelKey: "pre",
          legendItemKey :'pre',
          outerRadiusRatio: 0.5,
          sectorLabel: {
            color: "white",
            fontWeight: "bold",
            fontSize:10,
            fontFamily:'Roboto',
            formatter: ({ value }:any) => `${value}%`,
          },
        },
        {
          type: "donut",
          title: {
            text: "POST",
          },
          fills: ["#fff","#000000","#ED1C24","#FFCB05", "#418D18", "#BCBCBC","#355FD3"],
          angleKey: "post",
          sectorLabelKey: "post",
          legendItemKey :'post',
          innerRadiusRatio: 0.7,
          sectorLabel: {
            color: "white",
            fontWeight: "bold",
            fontSize:10,
            fontFamily:'Roboto',
            formatter: ({ value }:any) => `${value}%`,
          },
        },
      ],
    defaultColForChart:{
        columns:['color','pre','post'],
        start:0,
        end:9
    },
    graphInfo:[
        "This graph shows the potential improvement in Pipeline availability assuming the entire rationed qty would become goods in transit.",
    ],
    customizedStyles:{
        headerZoom:0.7, // default zoom is 1 
        headerContainerHeight:'30px', // default height is 60px
        agChartHeight:'86%'
    }
}