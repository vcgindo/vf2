export const chartParams1 = {
    title:'Top 10 Parent Locations : Max Pipeline Black/Red SKUs With Nil Rationed Stock For Receiving Locations',
    chartType:'stackedColumn',
    downloadName:'Top-10 Parent Loc (Max Pipeline for receiving loc)',
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
        fills: ['#000000', '#DA3535'],
        strokes: ['#ffffff', '#ffffff'],
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
        'This graph highlights the top 10 parent locations with max SKUs in Pipeline Black/Red with insufficient/nil rationed stock available for receiving locations',
        'To improve availability, expedite production/sourcing at these parent locations.'
    ],
    customizedStyles:{
        headerZoom:0.9, // default zoom is 1 
        headerContainerHeight:'40px', // default height is 60px
        agChartHeight:'86%'
    }
}


export const chartParams2 = {
    title:'Top 10 Parent Location: Max Continuous Pipeline Black/Red SKUs With Nil Rationed Stock Available For Receiving Location',
    chartType:'stackedColumn',
    downloadName:'Top-10 Parent Loc (Max Continuous for receiving loc)',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'Parent Location Name',
        Yaxis:'Count Of SKUs'
    },
    palette:{
        fills: ['#000000', '#DA3535'],
        strokes: ['#ffffff', '#ffffff'],
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
        'This graph highlights the top 10 parent locations with max number of SKUs in continuous Pipeline Black/Red > RLT and have insufficient/nil rationed stock available for receiving locations.',
        'To improve availability, expedite production/sourcing at these parent locations.'
    ],
    customizedStyles:{
        headerZoom:0.9, // default zoom is 1 
        headerContainerHeight:'40px', // default height is 60px
        agChartHeight:'86%'
    }
}