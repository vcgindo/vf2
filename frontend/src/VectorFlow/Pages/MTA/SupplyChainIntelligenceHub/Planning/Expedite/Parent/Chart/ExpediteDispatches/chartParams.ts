export const chartParams1 = {
    title:'Top 10 Parent Location: Max Pipeline Black/Red SKUs With Available Rationed Qty For Receiving Locations',
    chartType:'stackedColumn',
    downloadName:'Top 10 Parent Loc- (Max Pipeline Inv B/R Available at receiving loc)',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'Parent Location Name',
        Yaxis:'Count Of SKUs'
    },
    legend:{
        enabled:true,
        position:'bottom'
    },
    palette:{
        fills: ['#000000','#DA3535'],
        strokes: ["#ffffff", "#ffffff"],
    },
    chartKey:{
        Xaxis:['WHDescription'],
        Yaxis:['BlackCount','RedCount']
    },
    series:[ 
        {
            type:'bar',
            xKey:'WHDescription',  
            yKey:'BlackCount',
            yName:'Black',
            stacked:true,  
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'WHDescription',
            yKey:'RedCount',
            yName:'Red',
            stacked:true,
            barPadding:0.2,
        }
    ],
    defaultColForChart:{
        columns:['WHDescription','BlackCount','RedCount'],
        start:0,
        end:9
    }, 
    graphInfo:[
        "This graph highlights the top 10 parent locations with max SKUs in Pipeline Black/Red which have rationed qty available for receiving locations",
        "To improve availability, expedite dispatches from these parent locations.",
      ],
    customizedStyles:{
        headerZoom:0.7, // default zoom is 1 
        headerContainerHeight:'30px', // default height is 60px
        agChartHeight:'85%'
    }
}

// let firstLabelModified = false;

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
          outerRadiusRatio: 0.5,
          legendItemKey :'pre',
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
            text: "POST"
          },
          fills: ["#fff","#000000","#ED1C24","#FFCB05", "#418D18", "#BCBCBC","#355FD3"],
          angleKey: "post",
          sectorLabelKey: "post",
          innerRadiusRatio: 0.7,
          legendItemKey :'post',
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
    },
}