export const chartParams1 = {
    title:'Top 10 Transporters: Max LRs With On-Hand Black/Red SKUs Along With High Transport Ageing',
    chartType:'stackedColumn',
    downloadName:'Top 10 Transporters - Max LRs With On-Hand B/R SKUs Along With High Transport Ageing',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'Transporter Name',
        Yaxis:'Count Of LRs'
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
        'The graph illustrates the top 10 transporters having the maximum no. of LRs with SKUs in On-Hand Black/Red (shortage of on-handinventory) experiencing high transport ageing (Transportation Time > Standard Lead Time)',
        'Care needs to be taken to reduce the transportation time of LRs corresponding to above transporters',
        'Super Delay : Transportation Lead Time >= 1.5 x Standard Lead Time',
        'Delay : Transportation Lead Time > Standard Lead Time'
    ],
    customizedStyles:{
        headerZoom:0.9, // default zoom is 1 
        headerContainerHeight:'40px', // default height is 60px
        agChartHeight:'86%'
    }
}
