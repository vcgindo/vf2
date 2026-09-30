import { AgChartOptions } from 'ag-charts-community'
import { AgCharts } from 'ag-charts-react'
import { Dispatch, SetStateAction, useRef } from 'react'
import { SCChartContainer, SCChartMainContainer, SCHorizontalDivider, ChartWrapper } from './styles'
import VFModalCard from '../../../../../components/VectorFLOW/commons/VFModalCard'
import VFTable from "../../Common/VFTable";
import { GridRef } from '../../../../../VectorFlow/types/MDM'
import { renderToStaticMarkup } from 'react-dom/server';
interface SplitGrpahContainerProps {
  colDef: any,
  options: AgChartOptions,
  data: any,
  rowData: any,
  header: () => JSX.Element,
  graphTitle: string,
  graphTitleJSX?: JSX.Element,
  tableTitle: string,
  tableLoading?: boolean,
  chartLoading?: boolean,
  setTableLoading: Dispatch<SetStateAction<boolean>>,
  setChartLoading: Dispatch<SetStateAction<boolean>>,
  hideChart: boolean,
  toggleChart: Dispatch<SetStateAction<boolean>>,
  TooltipRenderer: (param: any) => string,
  graphType: number,
  date?: string,
  columnsData?: any,
  downloadFileName?: string,
}

const SplitGraphContainer = ({
  colDef,
  options,
  data,
  rowData,
  header,
  graphTitle,
  graphTitleJSX,
  tableTitle,
  setTableLoading,
  setChartLoading,
  hideChart,
  toggleChart,
  TooltipRenderer,
  graphType,
  columnsData,
}: SplitGrpahContainerProps) => {
  const chartRef = useRef<any>(null);
  const refGraph1 = useRef<GridRef>(null);

  const containerRef  = useRef<HTMLDivElement>(null);

  function extractTextContent(element: JSX.Element): string {
    const htmlString = renderToStaticMarkup(element);
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = htmlString;
    return tempDiv.textContent || '';
  }
  const downloadChartWithHeader = () => {
    if (containerRef.current) {
      const chartCanvas = containerRef.current.querySelector('canvas');
      if (!chartCanvas) {
        console.error("Chart canvas not found.");
        return;
      }

      const headerHeight = 40;
      const combinedCanvas = document.createElement('canvas');
      combinedCanvas.width = chartCanvas.width;
      combinedCanvas.height = chartCanvas.height + headerHeight;

      const ctx = combinedCanvas.getContext('2d');
      if (!ctx) {
        console.error("Failed to get canvas context.");
        return;
      }

      const titleText = graphTitleJSX ? extractTextContent(graphTitleJSX) : graphTitle || '';

      ctx.font = 'bold 16px Arial';  
      const textWidth = ctx.measureText(titleText).width;
      
      const xCoordinate = (combinedCanvas.width - textWidth) / 2;

      ctx.fillStyle = 'white';
      ctx.fillRect(0, 0, combinedCanvas.width, headerHeight);
      ctx.fillStyle = 'black';
      ctx.fillText(titleText, xCoordinate, 25);

      ctx.drawImage(chartCanvas, 0, headerHeight);

      const link = document.createElement('a');
      link.href = combinedCanvas.toDataURL('image/png');
      link.download = titleText || 'chart.png';
      link.click();
    }
  };
  

  const myCustomTheme = () => {
    switch (graphType) {
      case 1:
        return {
          palette: {
            fills: ['black', 'red', 'yellow', 'green', 'grey'],
            strokes: ['black', 'red', 'yellow', 'green', 'grey'],
          },
        }
      case 12:
        return {
          palette: {
            fills: columnsData?.map((column: any) => column?.color),
            strokes: columnsData?.map((column: any) => column?.color),
          },
        }

      case 4:
        return {
          palette: {
            fills: ["#AD5000", 'gray', '#459D55'],
            strokes: ["#AD5000", 'gray', '#459D55'],
          },
        }

      case 5:
        return {
          palette: {
            fills: ['gray'],
            strokes: ['gray'],
          },
        }

      case 6:
        return {
          palette: {
            fills: ['black', 'red'],
            strokes: ['black', 'red'],
          },
        }
      case 7:
        return {
          palette: {
            fills: ['black', 'red', 'yellow', 'green', 'blue', '#E8E8E8'],
            strokes: ['black', 'red', 'yellow', 'green', 'blue', '#E8E8E8'],
          },
        }
      case 8:
        return {
          palette: {
            fills: ['#BC3D81', '#FCADD7'],
            strokes: ['#BC3D81', '#FCADD7'],
          },
        }
      case 9:
        return {
          palette: {
            fills: ['#838282', '#CBCBCB'],
            strokes: ['#838282', '#CBCBCB'],
          },
        }
      case 10:
        return {
          palette: {
            fills: ['#F5B279', "#F09241", "#E36A00", "#AD5000", "#6A3000"],
            strokes: ['#F5B279', "#F09241", "#E36A00", "#AD5000", "#6A3000"],
          },
        }
      case 3: {
        return {
          palette: {
            fills: ['Grey'],
            strokes: ['Grey']
          }
        }
      }
      case 2: {
        return {
          palette: {
            fills: ['Grey'],
            strokes: ['Grey']
          }
        }
      }
      case 11:
        return {
          palette: {
            fills: ['#F5B279', "#F09241", "#E36A00", "#AD5000", "#6A3000"],
            strokes: ['#F5B279', "#F09241", "#E36A00", "#AD5000", "#6A3000"],
          },
        }
      case 14:
        return {
          palette: {
            fills: ['#AD5000'],
            strokes: ['#AD5000'],
          },
        }

      default:
        return {
          palette: {
            fills: ['black', 'red', 'green', 'yellow', 'grey'],
            strokes: ['black', 'red', 'green', 'yellow', 'grey'],
          },
        }
    }


  }


  const generateChart = (graphNo: number) => {

    switch (graphNo) {
      case 1:
        refGraph1.current?.api.createRangeChart({
          chartType: 'line',
          cellRange: {
            columns: ['dt', 'b', 'r', 'y', 'g', 'bl', 'w'],
          },

          chartThemeOverrides: {
            line: {
              series: {
                tooltip: {
                  renderer: TooltipRenderer
                },
                strokeWidth: 3

              },
              legend: {
                item: {
                  marker: {
                    shape: 'square'
                  }
                }
              }


            }
          }

        })
        break;
      case 12:
        refGraph1.current?.api.createRangeChart({
          chartType: 'line',
          cellRange: {
            columns: columnsData.map((column: any) => column.key),
          },

          chartThemeOverrides: {
            line: {
              series: {
                tooltip: {
                  renderer: (params: any) => TooltipRenderer({ ...params, labels: columnsData?.filter((column: any) => column.key !== 'month') })
                },
                strokeWidth: 3

              },
              axes: {
                category: {
                  crossLines: {
                    enabled: false,
                    strokeOpacity: 0,
                    stroke: 'white'
                  },
                  gridLine: {
                    enabled: false,
                  }

                }
              },
              legend: {
                item: {
                  marker: {
                    shape: 'square'
                  }
                }
              }


            }
          }

        })
        break;
      case 2:
        refGraph1.current?.api.createRangeChart({
          chartType: 'column',
          cellRange: {
            columns: ['rn', 'rc'],
          },

          chartThemeOverrides: {
            line: {
              series: {
                tooltip: {
                  renderer: TooltipRenderer
                },
                strokeWidth: 3

              },
              legend: {
                item: {
                  marker: {
                    shape: 'square'
                  }
                }
              }

            }
          }
        })
        break;
      case 3:
        refGraph1.current?.api.createRangeChart({
          chartType: 'column',
          cellRange: {
            columns: ['sn', 'rc'],
          },

          chartThemeOverrides: {
            line: {
              series: {
                tooltip: {
                  renderer: TooltipRenderer
                },
                strokeWidth: 3

              },
              legend: {
                item: {
                  marker: {
                    shape: 'square'
                  }
                }
              }

            }
          }
        })
        break;
      case 4:
        refGraph1.current?.api.createRangeChart({
          chartType: "stackedColumn",
          cellRange: {
            columns: ["ccr_n", "exceedDays", 'days', 'limit'],
          },
          seriesChartTypes: [
            { colId: "exceedDays", chartType: "stackedColumn" },
            { colId: "days", chartType: "stackedColumn" },
            { colId: "limit", chartType: "line" }
          ],
          chartThemeOverrides: {
            line: {
              series: {
                marker: {
                  size: 0
                }
              }
            },
            bar: {

              axes: {
                category: {
                  gridLine: {
                    enabled: false,
                  },


                  bottom: {
                    label: {
                      fontSize: 8,
                    },
                  },
                },
              },
              series: {

                highlightStyle: {

                  item: {

                    fill: "white",
                    fillOpacity: 0.2,
                  },
                },
                tooltip: {
                  renderer: TooltipRenderer,
                },
                strokeWidth: 1,
                strokeOpacity: 0,
              },
              legend: {
                item: {

                  label: {
                    fontSize: 10,
                  },

                  marker: {
                    shape: "square",
                  },
                },
              },
            },
          },
        });
        break;
      case 5:
        refGraph1.current?.api.createRangeChart({
          chartType: "stackedColumn",
          cellRange: {
            columns: ["ccr", "days"],
          },
          chartThemeOverrides: {
            bar: {
              axes: {
                category: {
                  gridLine: { enabled: false },

                  bottom: {
                    label: {
                      fontSize: 8,
                    },
                  },
                },
              },
              series: {
                highlightStyle: {
                  item: {
                    fill: "white",
                    fillOpacity: 0.2,
                  },
                },
                tooltip: {
                  renderer: TooltipRenderer,
                },
                strokeWidth: 1,
                strokeOpacity: 0,
              },
              legend: {
                item: {
                  label: {
                    fontSize: 10,
                  },

                  marker: {
                    shape: "square",
                  },
                },
              },
            },
          },
        });
        break;
      case 6:
        refGraph1.current?.api.createRangeChart({
          chartType: "stackedBar",
          cellRange: {
            columns: ["r", "bo", "ro"],
          },
          chartThemeOverrides: {
            bar: {
              axes: {
                category: {
                  position: 'left', // Position the category axis on the left
                  gridLine: {
                    enabled: false,
                  },
                  label: {
                    fontSize: 8,
                    rotation: 0
                  },
                  left: {
                    label: {
                      fontSize: 8,
                    },
                  },
                },
                number: {
                  position: 'bottom',
                  gridLine: { enabled: false },
                  label: {
                    fontSize: 8,
                  },
                },
              },
              series: {
                highlightStyle: {
                  item: {
                    fill: "white",
                    fillOpacity: 0.2,
                  },
                },
                tooltip: {
                  renderer: TooltipRenderer,
                },
                strokeWidth: 1,
                strokeOpacity: 0,
              },
              legend: {
                item: {
                  label: {
                    fontSize: 10,
                  },

                  marker: {
                    shape: "square",
                  },
                },
              },
            }
          },
        });
        break;
      case 7:
        refGraph1.current?.api.createRangeChart({
          chartType: "stackedColumn",
          cellRange: {
            columns: ["trailDept", "b", 'r', 'y', 'g', 'bl', 'w'],
          },
          chartThemeOverrides: {
            bar: {
              axes: {
                category: {
                  gridLine: { enabled: false },

                  bottom: {
                    label: {
                      fontSize: 8,
                    },
                  },
                },
              },
              series: {
                highlightStyle: {
                  item: {
                    fill: "white",
                    fillOpacity: 0.2,
                  },
                },
                tooltip: {
                  renderer: TooltipRenderer,
                },
                strokeWidth: 1,
                strokeOpacity: 0,
              },
              legend: {
                item: {
                  label: {
                    fontSize: 10,
                  },

                  marker: {
                    shape: "square",
                  },
                },
              },
            },
          },
        });
        break;
      case 10:
        refGraph1.current?.api.createRangeChart({
          chartType: "stackedColumn",
          cellRange: {
            columns: ["m", "0_2_p", "20_40_p", "40_60_p", "60_80_p", "80_100_p"],
          },
          chartThemeOverrides: {
            bar: {
              axes: {
                category: {
                  gridLine: { enabled: false },

                  bottom: {
                    label: {
                      fontSize: 8,
                    },
                  },
                },
              },
              series: {
                highlightStyle: {
                  item: {
                    fill: "white",
                    fillOpacity: 0.2,
                  },
                },
                tooltip: {
                  renderer: TooltipRenderer,
                },
                strokeWidth: 1,
                strokeOpacity: 0,
              },
              legend: {
                item: {
                  label: {
                    fontSize: 10,
                  },

                  marker: {
                    shape: "square",
                  },
                },
              },
            },
          },
        });
        break;

      case 11:
        refGraph1.current?.api.createRangeChart({
          chartType: "stackedColumn",
          cellRange: {
            columns: ["m", "1_2_d", "3_7_d", "8_15_d", "16_30_d"],
          },
          chartThemeOverrides: {
            bar: {
              axes: {
                category: {
                  gridLine: { enabled: false },

                  bottom: {
                    label: {
                      fontSize: 8,
                    },
                  },
                },
              },
              series: {
                highlightStyle: {
                  item: {
                    fill: "white",
                    fillOpacity: 0.2,
                  },
                },
                tooltip: {
                  renderer: TooltipRenderer,
                },
                strokeWidth: 1,
                strokeOpacity: 0,
              },
              legend: {
                item: {
                  label: {
                    fontSize: 10,
                  },

                  marker: {
                    shape: "square",
                  },
                },
              },
            },
          },
        });
        break;
      case 8:
        refGraph1.current?.api.createRangeChart({
          chartType: "line",
          cellRange: {
            columns: ["m", "otif", "otif_plus"],
          },
          chartThemeOverrides: {
            line: { // This should be 'line' since you are creating a line chart
              axes: {
                category: {
                  gridLine: { enabled: false },
                  bottom: {
                    label: {
                      fontSize: 8,
                    },
                  },
                },
                number: {
                  gridLine: { enabled: false },
                  label: {
                    fontSize: 10,
                    formatter: (params) => `${params.value}%`, // Format as percentage
                  },
                  min: 0, // Ensure Y-axis starts from 0
                },
              },
              series: {
                highlightStyle: {
                  item: {
                    fill: "white",
                    fillOpacity: 1,
                  },
                },
                tooltip: {
                  renderer: TooltipRenderer,
                },
                strokeWidth: 4,
                strokeOpacity: 1,
                marker: {
                  shape: "circle", // Ensure markers are square
                  size: 8, // Adjust the size as needed
                },
              },
              legend: {
                item: {
                  label: {
                    fontSize: 10,
                  },
                  marker: {
                    shape: "square",
                  },
                },
              },
            },
          },
        });
        break;
      case 9:
        refGraph1.current?.api.createRangeChart({
          chartType: "line",
          cellRange: {
            columns: ["m", "ot", "if"],
          },
          chartThemeOverrides: {
            line: { // This should be 'line' since you are creating a line chart
              axes: {
                category: {
                  gridLine: { enabled: false },
                  bottom: {
                    label: {
                      fontSize: 8,
                    },
                  },
                },
                number: {
                  gridLine: { enabled: false },
                  label: {
                    fontSize: 10,
                    formatter: (params) => `${params.value}%`, // Format as percentage
                  },
                  min: 0, // Ensure Y-axis starts from 0
                },
              },
              series: {
                highlightStyle: {
                  item: {
                    fill: "white",
                    fillOpacity: 1,
                  },
                },
                tooltip: {
                  renderer: TooltipRenderer,
                },
                strokeWidth: 4,
                strokeOpacity: 1,
                marker: {
                  shape: "circle", // Ensure markers are square
                  size: 8, // Adjust the size as needed
                },
              },
              legend: {
                item: {
                  label: {
                    fontSize: 10,
                  },
                  marker: {
                    shape: "square",
                  },
                },
              },
            },
          },
        });
        break;
      case 14:
        refGraph1.current?.api.createRangeChart({
          chartType: "stackedBar",
          cellRange: {
            columns: ["r", "co"],
          },
          chartThemeOverrides: {
            bar: {
              axes: {
                category: {
                  position: 'left', // Position the category axis on the left
                  gridLine: { enabled: false },
                  label: {
                    fontSize: 8,
                    rotation: 0
                  },
                  left: {
                    label: {
                      fontSize: 8,
                    },
                  },
                },
                number: {
                  position: 'bottom',
                  gridLine: { enabled: false },
                  label: {
                    fontSize: 8,
                  },
                },
              },
              series: {
                highlightStyle: {
                  item: {
                    fill: "white",
                    fillOpacity: 0.2,
                  },
                },
                tooltip: {
                  renderer: TooltipRenderer,
                },
                strokeWidth: 1,
                strokeOpacity: 0,
              },
              legend: {
                item: {
                  label: {
                    fontSize: 10,
                  },

                  marker: {
                    shape: "square",
                  },
                },
              },
            }
          },
        });
        break;
      default:
        <></>
    }


  }




  return (
    <div style={{ width: "100%" , height:"100%"}}>


      <SCChartContainer style={{ border: '1px solid #CCCCCC', margin: '2px', height: '100%', display: 'flex', flexDirection: 'column'}} height={'100%'}>
        <SCChartMainContainer style={{ zoom: 1 }}>
          {header()}
        </SCChartMainContainer>

        <SCHorizontalDivider />
        <ChartWrapper>
          <div style={{ height: '100%', width: '100%' }} ref={containerRef}>
            <div className="title" style={{ backgroundColor: 'white', height: '40px', display: 'flex', justifyContent: 'right', alignItems: 'center' }}>
              <div style={{ fontSize: '10px', fontWeight: 500, textAlign: 'center', margin: '0 auto' }}>
                {graphTitle || graphTitleJSX}
              </div>
              <div style={{ marginLeft: '0 10px -5px', marginBottom: '-5px' }} onClick={downloadChartWithHeader}>
                <img src='/assets/img/mto/RMPMBufferTrend/download.svg' style={{ color: "#CCCCCC", paddingBottom: '5px' }} height={15} width={15} color={"#CCCCCC"} />
              </div>

            </div>
            <div className='chart-wrapper' style={{ flex: 1 , height:"90%"}}>
              <AgCharts ref={chartRef} options={{ ...options, data: data }} />
            </div>
          </div>
        </ChartWrapper>

        <VFModalCard
          openModal={hideChart}
          closeModal={() => toggleChart(false)}
          headerIcon=''
          headerText={tableTitle}
          headerBgColor=""
          headerTextColor="#00000"
          paddingLeftAndRight={27}
          closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}>
          <div className="ag-theme-planning" style={{ width: '1000px' }}>
            <VFTable

              ref={refGraph1}
              columnDefs={colDef}
              rowData={rowData}
              enableCharts={true}
              enableRangeSelection={true}
              rowSelection="multiple"
              statusBar={{
                statusPanels: [
                  { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
                  { statusPanel: 'agTotalRowCountComponent', align: 'left' },
                  { statusPanel: 'agFilteredRowCountComponent', align: 'left' },
                  { statusPanel: 'agSelectedRowCountComponent', align: 'left' },
                  { statusPanel: 'agAggregationComponent', align: 'left' },
                ],
              }} onGridReady={() => { setTableLoading(false); generateChart(graphType), setChartLoading(false); }}
              chartToolPanelsDef={
                {
                  panels: []
                }
              }
              disableZoomScaling={true}
              defaultColDef={{
                floatingFilter: true,
                filter: "agMultiColumnFilter",
                flex: 1,
              }}
              chartThemes={['myCustomTheme']}
              customChartThemes={{
                'myCustomTheme': myCustomTheme()
              }}
              height={'480px'}
            />
          </div>
        </VFModalCard>
      </SCChartContainer>
    </div>

  )
}

export default SplitGraphContainer