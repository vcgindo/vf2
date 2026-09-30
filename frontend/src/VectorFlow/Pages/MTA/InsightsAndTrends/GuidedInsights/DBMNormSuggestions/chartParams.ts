export const chartParams1 = {
    title:'Top 10 Locations: Max No. Of DBM Suggestions',
    chartType:'stackedColumn',
    downloadName:'Top 10 Loc- (Max No. Of DBM Suggestions)',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'Location Name',
        Yaxis:'No Of Suggestions'
    },
    legend:{
        enabled:true,
        position:'right',
        item:{
            label:{
                fontSize:8
            },
            marker:{
                size:8
            }
        }
    },
    palette:{
        fills: ["#355FD3", "#D0A928", "#403F3F", "#00000026"],
        strokes: ["#ffffff", "#ffffff"],
    },
    chartKey:{
        Xaxis:['location'],
        Yaxis:['NormInc','NormDec']
    },
    series:[
        {
            type:'bar',
            xKey:'location',
            yKey:'NormInc',
            yName:'Norm Inc',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'location',
            yKey:'NormDec',
            yName:'Norm Dec',
            stacked:true,
            barPadding:0.2,
        }
    ],
    defaultColForChart:{
        columns:['location','NormInc','NormDec'],
        start:0,
        end:9
    },
    graphInfo: [
        "This chart highlights the top 10 locations based on the maximum no. of suggestions for norm increase or decrease.",
    ],
    customizedStyles:{
        headerZoom:0.7, // default zoom is 1 
        headerContainerHeight:'25px', // default height is 60px
        agChartHeight:'80%'
    },
}


export const chartParams2 = {
    title:'Distribution Of Current Active DBM Suggestions',
    chartType:'pie',
    downloadName:'Distribution Of Current Active DBM Suggestions',
    palette:{
        fills: ["#D0A928" ,"#355FD3" , "#403F3F", "#00000026"],
        strokes: ["#ffffff", "#ffffff"],
    },
    legend:{
        enabled:true,
        position:'right',
        item:{
            label:{
                fontSize:8
            },
            marker:{
                size:8
            }
        }
    },    
    chartKey:{
        Xaxis:['suggestion'],
        Yaxis:['count']
    },
    series: [
        {
            type:'pie',
            xKey:'suggestions',
            yKey:'count',
            yName:'Count',
            stacked:true,
            barPadding:0.2,
        },
    ],
    defaultColForChart:{
        columns:["suggestion", "count"],
        start:0,
        end:9
    },
    graphInfo:[
        "This pie chart highlights the distribution of SKU Location-wise DBM Suggestion status as on today.",
    ],
    customizedStyles:{
        headerZoom:0.7, // default zoom is 1 
        headerContainerHeight:'25px', // default height is 60px
        agChartHeight:'80%'
    },
}


// {
//     type: "pie",
//     title: {
//       text: "PRE",
//     },
//     fills: ["#000000","#ED1C24","#FFCB05", "#418D18", "#BCBCBC","#355FD3"],
//     angleKey: "pre",
//     sectorLabelKey: "pre",
//     legendItemKey :'pre',
//     outerRadiusRatio: 0.5,
//     sectorLabel: {
//       color: "white",
//       fontWeight: "bold",
//       fontSize:10,
//       fontFamily:'Roboto',
//       formatter: ({ value }:any) => `${value}%`,
//     },
//   },


export const chartParams3 = {
    title:'Top 10 Products: Max No. Of DBM Suggestions',
    chartType:'stackedColumn',
    downloadName:'Top 10 Products: Max No. Of DBM Suggestions',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'SKU Code',
        Yaxis:'No Of suggestions'
    },
    legend:{
        enabled:true,
        position:'right',
        item:{
            label:{
                fontSize:8
            },
            marker:{
                size:8
            }
        }
    },
    palette:{
        fills: ["#355FD3", "#D0A928", "#403F3F", "#00000026"],
        strokes: ["#ffffff", "#ffffff"],
    },
    chartKey:{
        Xaxis:['sku'],
        Yaxis:["NormInc", "NormDec"]
    },
    series:[
        {
            type:'bar',
            xKey:'sku',
            yKey:'NormInc',
            yName:'Norm Inc',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'sku',
            yKey:'NormDec',
            yName:'Norm Dec',
            stacked:true,
            barPadding:0.2,
        }
    ],
    defaultColForChart:{
        columns:['sku',"NormInc", "NormDec"],
        start:0,
        end:9
    },
    graphInfo: [
        "This chart highlights the top 10 products based on the maximum no. of suggestions for norm increase or decrease",
    ],
    customizedStyles:{
        headerZoom:0.7, // default zoom is 1 
        headerContainerHeight:'25px', // default height is 60px
        agChartHeight:'80%'
    },
}


export const chartParams4 = {
    title:'Ageing categorization Of DBM suggestions',
    chartType:'stackedColumn',
    downloadName:'Ageing categorization Of DBM suggestions',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'Ageing',
        Yaxis:'No Of suggestions'
    },
    legend:{
        enabled:true,
        position:'right',
        item:{
            label:{
                fontSize:8
            },
            marker:{
                size:8
            }
        }
    },
    palette:{
        fills: ["#355FD3", "#D0A928", "#403F3F", "#00000026"],
        strokes: ["#ffffff", "#ffffff"],
    },
    chartKey:{
        Xaxis:['age'],
        Yaxis:['NormInc','NormDec']
    },
    series:[
        {
            type:'bar',
            xKey:'age',
            yKey:'NormInc',
            yName:'Norm Inc',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'age',
            yKey:'NormDec',
            yName:'Norm Dec',
            stacked:true,
            barPadding:0.2,
        }
    ],
    defaultColForChart:{
        columns:["age", "NormInc", "NormDec"],
        start:0,
        end:9
    },
    graphInfo:[
        "This chart highlights the pendency of DBM suggestions. DBM Suggestion Age = Today - Suggestion Generation Date",
    ],
    customizedStyles:{
        headerZoom:0.7, // default zoom is 1 
        headerContainerHeight:'25px', // default height is 60px
        agChartHeight:'80%'
    },
}