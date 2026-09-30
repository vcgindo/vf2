export const chartParams1 = {
    title:'Top 10 Locations: Max On-Hand Black/Red SKUs Along With High Transport Ageing',
    chartType:'stackedColumn',
    downloadName:'Top 10 Loc- Max On-Hand B/R SKUs Along With High Transport Ageing',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'Receiving Location Name',
        Yaxis:'Count Of SKUs'
    },
    legend:{
        enabled:true,
        position:'bottom'
    },
    palette:{
        fills:['#0c7528','#570dbf'],
        strokes: ['#ffffff', '#ffffff']
    },
    chartKey:{
        Xaxis:['name'],
        Yaxis:['superdelay','delay']
    },
    series:[
        {
            type:'bar',
            xKey:'name',
            yKey:'superdelay',
            yName:'Super Delay',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'name',
            yKey:'delay',
            yName:'Delay',
            stacked:true,
            barPadding:0.2,
        },
    ],
    defaultColForChart:{
        columns:['name','superdelay','delay'],
        start:0,
        end:9
    },
    graphInfo: [
        'The graph illustrates the top 10 receiving locations having the maximum no. of SKUs in On-Hand Black/Red (shortage of on-hand inventory) experiencing high transport ageing (Transportation Time > Standard Lead Time)',
        'Care needs to be taken to reduce the transportation time in these locations or adjust the RLTs for Norm calculation',
        'Super Delay : Transportation Lead Time >= 1.5 x Standard Lead Time',
        'Delay : Transportation Lead Time > Standard Lead Time'
    ],
    customizedStyles:{
        headerZoom:0.9, // default zoom is 1 
        headerContainerHeight:'40px', // default height is 60px
        agChartHeight:'86%'
    }
}
