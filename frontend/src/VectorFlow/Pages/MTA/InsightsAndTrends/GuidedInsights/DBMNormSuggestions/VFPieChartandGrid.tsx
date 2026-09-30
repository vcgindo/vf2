import { useState, useRef } from 'react';
import VFInfoToolTip from "../../../../../../components/VectorFLOW/commons/VFInfoToolTip";
import { AgCharts } from 'ag-charts-react';
import { SCChartHeaderContainer, SCChartHeader, SCChartContainer, SCHorizontalDivider} from '../../../../../../components/VectorFLOW/commons/VFCharts/styles';
import VFChartTable from '../../../../../../components/VectorFLOW/commons/VFChartsTable';
import { GridRef } from '../../../../../../VectorFlow/types/MDM';

const defaultStyles = {
  headerZoom:1,
  headerContainerHeight:'60px',
  agChartHeight:'80%'
}

const PieChartandGrid = (props:any) => {
    const {
        chartParams,
        height,
        colDefs,
        rowData,
        chartProps,
        containerStyle
    } = props;

    const {palette, chartType, defaultColForChart, graphInfo, title, customizedStyles=defaultStyles, downloadName } = chartParams

    const [hideChart,setHideChart] = useState<boolean>(false)
    const gridRef = useRef<GridRef>()
    const chartRef = useRef<any>(null)
    const [isHovered, setIsHovered] = useState(false);
    const imgSrc = isHovered
    ? '/assets/img/downlod-icon-hover.svg'
    : '/assets/img/downlod-icon.svg';

    const containerRef  = useRef<HTMLDivElement>(null);
  
    const downloadChartWithHeader = () => {
        if (containerRef.current) {
            const chartCanvas = containerRef.current.querySelector('canvas');
            if (!chartCanvas) {
                console.error("Chart canvas not found.");
                return;
            }
    
            const titleText = title || '';
            const fontSize = 16;
            const lineHeight = 24;
            const padding = 10;
    
            const tempCanvas = document.createElement('canvas');
            const tempCtx = tempCanvas.getContext('2d');

            if (!tempCtx) {
                console.error("Failed to get temp canvas context.");
                return;
            }

            tempCtx.font = `bold ${fontSize}px Arial`;
            const maxWidth = chartCanvas.width - 2 * padding;
            const words = titleText.split(' ');
            const lines = [];
            let currentLine = '';
    
            for (const word of words) {
                const testLine = currentLine + (currentLine ? ' ' : '') + word;
                const testWidth = tempCtx.measureText(testLine).width;
                if (testWidth > maxWidth) {
                    lines.push(currentLine);
                    currentLine = word;
                } else {
                    currentLine = testLine;
                }
            }
            if (currentLine) lines.push(currentLine);
    
            const headerHeight = lines.length * lineHeight;
    
            const combinedCanvas = document.createElement('canvas');
            combinedCanvas.width = chartCanvas.width;
            combinedCanvas.height = chartCanvas.height + headerHeight;
    
            const ctx = combinedCanvas.getContext('2d');
            if (!ctx) {
                console.error("Failed to get canvas context.");
                return;
            }
    
            ctx.fillStyle = 'white';
            ctx.fillRect(0, 0, combinedCanvas.width, combinedCanvas.height);
            ctx.font = `bold ${fontSize}px Arial`;
            ctx.fillStyle = 'black';
    
            lines.forEach((line, i) => {
                const textWidth = ctx.measureText(line).width;
                const x = (combinedCanvas.width - textWidth) / 2;
                const y = (i + 1) * lineHeight - (lineHeight - fontSize) / 2;
                ctx.fillText(line, x, y);
            });
    
            ctx.drawImage(chartCanvas, 0, headerHeight);
    
            const sanitizedFilename = (titleText || 'chart')
                .replace(/[/\\?%*:|"<>]/g, '_')
                .trim();
    
            const link = document.createElement('a');
            link.href = combinedCanvas.toDataURL('image/png');
            link.download = `${sanitizedFilename}.png`;
            link.click();
        }
    };

    const pieChartOptions: any = {
      data: rowData,
      theme: {
        palette: {
          fills: palette?.fills || ["#355FD3", "#D0A928", "#403F3F", "#00000026"],
          strokes: palette?.strokes || ["#ffffff", "#ffffff"]
        }
      },

      padding: {
        top: 20,
        right: 40,
        bottom: 40,
        left: 40
      },
      series: [
        {
          type: 'pie',
          angleKey: 'count',
          calloutLabelKey: 'suggestion',
          sectorLabelKey: 'count',
          outerRadiusRatio: 1, 
          innerRadiusRatio: 0,    
          calloutLine: {
            length: 10,
            strokeWidth: 1
          },
          sectorLabel: {
            color: 'white',
            fontWeight: 'bold',
            fontSize: 10,
            fontFamily: 'Roboto',
            formatter: ({ value }: any) => `${value}`
          },
          calloutLabel: {
            fontSize: 8,
            fontFamily: 'Roboto',
            minAngle: 20  
          },
          tooltip: {
            enabled: true,
            renderer: (params: any) => {
              const color = params.fill || '#666666';
              return `
                <div style="background: #6C696A; border-radius: 6px; overflow: hidden; text-align: center; min-width: 140px;">
                  <div style="color: white; padding: 6px 10px; background-color: ${color}; font-weight: bold;">
                    ${params.datum.suggestion || 'Unknown'}
                  </div>
                  <div style="color: black; padding: 8px 10px; background-color: #ede7e9ff;">
                    ${params.datum.count}
                  </div>
                </div>
              `;
            }
          }
        }
      ],
      legend: {
        enabled: true,
        position: 'right',
        spacing: 20, 
        item: {
          label: {
            fontSize: 8
          },
          marker: {
            size: 8
          }
        }
      }
    };

    return (
        <SCChartContainer height={height} style={containerStyle} ref={containerRef}>

            <VFChartsHeader hideChart={hideChart} styles={customizedStyles} graphInfo={graphInfo} setHideChart={setHideChart} title={title}  />

            <SCHorizontalDivider/>

            <div style={{display:'flex', justifyContent: 'flex-end', alignItems: 'center', marginRight:'20px' , overflow:"hidden"}}>
                <img 
                    src={imgSrc}  
                    height={13} 
                    width={13} 
                    onClick={downloadChartWithHeader}
                    style={{cursor:'pointer'}} 
                    onMouseEnter={() => setIsHovered(true)}
                    onMouseLeave={() => setIsHovered(false)} >
                </img>                  
            </div>

            {!hideChart && (
              <AgCharts ref={chartRef} style={{minHeight:'80%',height:customizedStyles.agChartHeight}} options={pieChartOptions} />
            )}

            <VFChartTable 
                chartType={chartType} 
                downloadName={downloadName} 
                palette={palette} 
                title={title} 
                defaultColForCustomGraph={defaultColForChart} 
                setHideChart={setHideChart} 
                hideChart={hideChart} 
                gridRef={gridRef} 
                colDefs={colDefs} 
                rowData={rowData} 
                chartProps={chartProps}
                gridSpecificChartOptions={pieChartOptions}
                />
    
        </SCChartContainer>
    )
}

export default PieChartandGrid;

const VFChartsHeader = (props:any) =>{
    const { hideChart, styles, graphInfo, setHideChart, title} = props;
    return (
        <SCChartHeaderContainer style={{height:styles.headerContainerHeight}}>
            <div style={{display:'flex',width:'100%',justifyContent:'center' , overflow:"hidden"}}><SCChartHeader style={{marginRight:10,zoom:styles.headerZoom}}>{title}</SCChartHeader></div>
            <div style={{display:'flex',alignItems:'center',marginRight:'18px'}}>
                <div style={{marginBottom:'-5px',marginRight:'10px'}}><VFInfoToolTip infoList={graphInfo}/></div>
                {!hideChart && <img src="/assets/img/VectorFLOW/BPR/expand-graph.svg" width={15} height={15} alt="" onClick={()=>setHideChart(true)}/>}
            </div>
        </SCChartHeaderContainer>
    )
}