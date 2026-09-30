export const chartParams1 = {
    title:'Top 10 Locations: Categorization Of Pending Quantity',
    chartType:'stackedColumn',
    downloadName:'Top 10 Loc (Category of Pending Quantity)',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'Location Name',
        Yaxis:'No Of Orders'
    },
    legend:{
        enabled:true,
        position:'bottom'
    },
    palette:{
        fills: ['#ED1C24','#E3812D','#355FD3'],
        strokes: ['#ffffff', '#ffffff']
    },
    chartKey:{
        Xaxis:['location'],
        Yaxis:['overdue','due','others']
    },
    series:[
        {
            type:'bar',
            xKey:'location',
            yKey:'overdue',
            yName:'Overdue',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'location',
            yKey:'due',
            yName:'Due',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'location',
            yKey:'others',
            yName:'Others',
            stacked:true,
            barPadding:0.2,
        }
    ],
    defaultColForChart:{
        columns:['location','overdue','due','others'],
        start:0,
        end:9
    },
    graphInfo: [
        'This graph highlights the top 10 locations with max number of over due orders. It also captures the status of due & other orders from pending orders file.',
        'Overdue orders - Due date crossed | Due Orders - Due dates of today or in the future | Other Orders - PSO Quantity'
    ],
    customizedStyles:{
        headerZoom:0.9, // default zoom is 1 
        headerContainerHeight:'40px', // default height is 60px
        agChartHeight:'86%'
    }
}


export const chartParams2 = {
    title:'Top 10 Locations: Max SKUs With Gap > 67% Of Requirement',
    chartType:'stackedColumn',
    downloadName:'Top 10 Loc (Max SKUs With Gap > 67% Of Req)',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'Location Name',
        Yaxis:'No Of SKUs'
    },
    legend:{
        enabled:true,
        position:'bottom'
    },
    palette:{
        fills: ['#F02424','#E3812D','#418D18'],
        strokes: ['#ffffff', '#ffffff'],
    },
    chartKey:{
        Xaxis:['location'],
        Yaxis:['greater','between','smaller']
    },
    series:[
        {
            type:'bar',
            xKey:'location',
            yKey:'greater',
            yName:'Gap > 67%',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'location',
            yKey:'between',
            yName:'33% <= Gap <= 67%',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'location',
            yKey:'smaller',
            yName:'Gap < 33%',
            stacked:true,
            barPadding:0.2,
        }
    ],
    defaultColForChart:{
        columns:['location','greater','between','smaller'],
        start:0,
        end:9
    },
    graphInfo:[
        'This Graph highlights the top 10 locations with max no of SKUs with Gap > 67% of requirement.',
        'Gap = Requirement - Rationed Qty',
        'Requirement = Norm Requirement + Spike Requirement + Relevant PSO & CNR Requirement'
    ],
    customizedStyles:{
        headerZoom:0.9, // default zoom is 1 
        headerContainerHeight:'40px', // default height is 60px
        agChartHeight:'86%'
    }
}