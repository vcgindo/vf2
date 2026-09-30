export const chartParams1 = {
    title:'Top 10 Locations: Max SKUs In Continuous Pipeline Black Or Red Ageing Greater Than RLT',
    chartType:'stackedColumn',
    downloadName:'Top 10 Loc (Max SkU In Conti Pipeline B or R Greater than RLT)',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'Location Name',
        Yaxis:'Count Of SKUs'   
    },
    palette:{
        fills: [ '#0a0a0a','#F02424'],
        strokes: ['#ffffff', '#ffffff'],
    },
    legend:{
        enabled:true,
        position:'bottom'
    },
    chartKey:{
        Xaxis:['location'],
        Yaxis:['blackCount','redCount']
    },
    series:[
        {
            type:'bar',
            xKey:'location',
            yKey:'blackCount',
            yName:'Black',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'location',
            yKey:'redCount',
            yName:'Red',
            stacked:true,
            barPadding:0.2,
        }
    ],
    defaultColForChart:{
        columns:['location','blackCount','redCount'],
        start:0,
        end:9
    },
    graphInfo: [
        'This graph highlights the top 10 locations with the highest number of SKUs continuously in Pipeline black, red or combination of black and red, surpassing the RLT'
    ],
    customizedStyles:{
        headerZoom:0.9, // default zoom is 1 
        headerContainerHeight:'40px', // default height is 60px
        agChartHeight:'86%'
    }
}


export const chartParams2 = {
    title:'Top 10 SKUs: Max Number Of Locations Where The SKU Has Pipeline Black/Red Ageing Greater Than RLT',
    chartType:'stackedColumn',
    downloadName:'Top 10 SKU (Max No of Loc Where SKU has Pipeline B/R Greater than RLT)',
    LabelPosition:'bottom',
    Labels:{
        Xaxis:'SKU Code',
        Yaxis:'Count Of Locations'   
    },
    palette:{
        fills: [ '#0a0a0a','#F02424'],
        strokes: ['#ffffff', '#ffffff'],
    },
    legend:{
        enabled:true,
        position:'bottom'
    },
    chartKey:{
        Xaxis:['sku'],
        Yaxis:['blackCount','redCount']
    },
    series:[
        {
            type:'bar',
            xKey:'sku',
            yKey:'blackCount',
            yName:'Black',
            stacked:true,
            barPadding:0.2,
        },
        {
            type:'bar',
            xKey:'sku',
            yKey:'redCount',
            yName:'Red',
            stacked:true,
            barPadding:0.2,
        }
    ],
    defaultColForChart:{
        columns:['sku','blackCount','redCount'],
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