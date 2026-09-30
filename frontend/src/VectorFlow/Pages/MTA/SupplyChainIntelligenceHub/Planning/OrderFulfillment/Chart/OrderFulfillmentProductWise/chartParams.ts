export const chartParams1 = {
    title:'Top 10 Products: Categorization Of Pending Quantity',
    chartType:'stackedColumn',
    downloadName:'Top-10 Prd (Category of Pending Quantity)',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'Product Name',
        Yaxis:'Pending Quantity'
    },
    legend:{
        enabled:true,
        position:'bottom'
    },
    palette:{
        fills: ['#ED1C24','#E3812D','#355FD3'],
        strokes: ['#ffffff', '#ffffff'],
    },
    chartKey:{
        Xaxis:['product'],
        Yaxis:['overdue','due','others']
    },
    series:[
        {
            type:'bar',
            xKey:'product',
            yKey:'overdue',
            yName:'Overdue',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'product',
            yKey:'due',
            yName:'Due',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'product',
            yKey:'others',
            yName:'Others',
            stacked:true,
            barPadding:0.2,
        }
    ],
    defaultColForChart:{
        columns:['product','overdue','due','others'],
        start:0,
        end:9
    },
    graphInfo:[
        'This graph highlights the top 10 products with maximum number of over due quantities and distribution of due and other quantities from pending orders file.',
        'Overdue qty indicate those with past due dates, due represents qty with due dates of today in the future, while others include qty without due dates.'
    ],
    customizedStyles:{
        headerZoom:0.9, // default zoom is 1 
        headerContainerHeight:'40px', // default height is 60px
        agChartHeight:'86%'
    }
}


export const chartParams2 = {
    title:'Top 10 Products: Max Locations With Gap > 67% of Requirement',
    chartType:'stackedColumn',
    downloadName:'Top-10 Prd (Max Locs With Gap > 67% of Req)',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'Product Name',
        Yaxis:'No. Of Locations'
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
        Xaxis:['product'],
        Yaxis:['greater','between','smaller']
    },
    series:[
        {
            type:'bar',
            xKey:'product',
            yKey:'greater',
            yName:'Gap > 67%',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'product',
            yKey:'between',
            yName:'33% <= Gap <= 67%',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'product',
            yKey:'smaller',
            yName:'Gap < 33%',
            stacked:true,
            barPadding:0.2,
        }
    ],
    defaultColForChart:{
        columns:['product','greater','between','smaller'],
        start:0,
        end:9
    },
    graphInfo:[
        'This Graph highlights the top 10 products with max no of locations where Gap in the product > 67% of requirement.',
        'Gap = Requirement - Rationed Qty',
        'Requirement = Norm Requirement + Spike Requirement + Relevant PSO & CNR Requirement'
    ],
    customizedStyles:{
        headerZoom:0.9, // default zoom is 1 
        headerContainerHeight:'40px', // default height is 60px
        agChartHeight:'86%'
    }
}