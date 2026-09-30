import Chart from "../../../../../../components/VectorFLOW/commons/Chart";
import VFModalCard from "../../../../../../components/VectorFLOW/commons/VFModalCard";
import { Chart as ChartJS, ChartData, ChartDataset, ChartOptions } from "chart.js";
import { 
  SCChartContainer, 
  SCSeasonalityContainer, 
  SCSeasonalityStatusDetails,
  SCSeasonalityDetailsTitle,
  SCSeasonalityDetailsBody,
  SCText,
  SCCheckBoxRow,
  SCCheckBoxContainer,
  SCHorizontalDivider,
  SCDataRow,
  SCDataNode,
  SCVerticalDivider
 } from "./styles";
 import Checkbox from "../../../../../../components/commons/Checkbox";
//  import {enIN} from 'date-fns/locale';
 import { useRef, useState, useEffect } from "react";
import { DailyData } from "../../../../../types/MDM";
import { useUserData } from "../../../../../../context";





interface SeasonalityChartModalProps{
  rowData:any,
  chartData:any
  normChangeData:any
  isModalOpen:boolean,
  closeModal:()=>void,

}




const SeasonalityChartModal = ({rowData,chartData,normChangeData,isModalOpen,closeModal}:SeasonalityChartModalProps) => {

  const {user} = useUserData()
  const {theme_ui} = user.user

  const customTooltip = (context:any)=> {
    const getCurrentDate = () => {
      // const splitDateString = tooltip.dataPoints[0].label.split(',');
      // const currentDate = `${splitDateString[0].split(' ')[1]}-${splitDateString[0].split(' ')[0]}-${splitDateString[1].trim()}`;
      // return currentDate
      return tooltip.dataPoints[0].label;
    }
  
    const getCurrentStock = () => {
      const dataIndex = tooltip.dataPoints[0].dataIndex;
      const stockDataSet = context.chart.data.datasets.find((data:ChartDataset) => data.label === 'Stock');
      return stockDataSet.data[dataIndex]
    }
  
    const getCurrentGIT = () => {
      const dataIndex = tooltip.dataPoints[0].dataIndex;
      const gitDataSet = context.chart.data.datasets.find((data:ChartDataset) => data.label === 'GIT');
      return gitDataSet.data[dataIndex]
    }

    const getNormChangeReason = () => {
      const dataIndex = tooltip.dataPoints[0].dataIndex;
      const currentDate = new Date(chart.data.labels[dataIndex]);
      
      const normObject = normChangeData.find((data:DailyData)=> {
        const normChangeDate = new Date(data.date);
        if(
            currentDate.getDay() === normChangeDate.getDay() &&
            currentDate.getMonth() === normChangeDate.getMonth() &&
            currentDate.getFullYear() === normChangeDate.getFullYear()
          ){
            return true;
          }
          return false;
      });

      if(normObject){
        return normObject.change_reason
      }
      return;
    }
    
  
    const {chart, tooltip} = context;

    let tooltipEl:HTMLElement = chart.canvas.parentNode.querySelector('div');
  
    
    if(!tooltipEl){
      tooltipEl = document.createElement('div');
      tooltipEl.style.width = '160px';
      tooltipEl.style.height = '200px';
      tooltipEl.style.backgroundColor = '#ffffff';
      tooltipEl.style.color = '#000000';
      tooltipEl.style.fontFamily = 'Roboto';
      tooltipEl.style.boxShadow = '-6px 6px 16px #0000000F';
      tooltipEl.style.display = 'flex';
      tooltipEl.style.flexDirection = 'column';
      tooltipEl.style.justifyContent = 'space-evenly';
      tooltipEl.style.borderRadius = '4px';
  
    }
  
    if (tooltip.opacity === 0) {
      tooltipEl.style.opacity = '0';
      return;
    }
    
    const toolTipHTML = `
      <h3 style="text-decoration:underline;text-align:center;">${getCurrentDate()}</h3>
      <div style="display:flex;justify-content:space-between;">
        <p>Start Date</p>
        <p style="font-weight:600;">${rowData.sd}</p>
      </div>
      <div style="display:flex;justify-content:space-between;">
        <p>Norm</p>
        <p style="font-weight:600;">${tooltip.dataPoints[0].raw}</p>
      </div>
      <div style="display:flex;justify-content:space-between;">
        <p>Original Norm</p>
        <p style="font-weight:600;">${rowData.onm}</p>
      </div>
      <hr style="width:100%;border:none;border-top:1px dashed #B2B2B2;"/>
      <div style="display:flex;justify-content:space-between;">
        <p>Stock</p>
        <p style="font-weight:500;">${getCurrentStock()}</p>
      </div>
      <div style="display:flex;justify-content:space-between;">
        <p>GIT</p>
        <p style="font-weight:600;">${getCurrentGIT()}</p>
      </div>
      <div style="display:flex;justify-content:space-between;">
        <p>Reason</p>
        <p style="font-weight:600;">${getNormChangeReason()}</p>
      </div>
  
    `
  
    tooltipEl.appendChild(document.createElement('p'));
    // console.log(tooltipEl);
  
    tooltipEl.innerHTML = toolTipHTML;
  
    chart.canvas.parentNode.appendChild(tooltipEl);
  
    const {offsetLeft: positionX, offsetTop: positionY} = chart.canvas;
  
    // Display, position, and set styles for font
    tooltipEl.style.opacity = '1';
    tooltipEl.style.position='absolute';
    tooltip
    tooltipEl.style.top = positionY + tooltip.caretY + 'px';
    tooltipEl.style.left = positionX + tooltip.caretX + 'px';
    tooltipEl.style.font = tooltip.options.bodyFont.string;
    tooltipEl.style.padding = tooltip.options.padding + 'px ' + tooltip.options.padding + 'px';
    // return tooltipEl;
  
  }

  const chartOptions:ChartOptions = {
    responsive:true,
    maintainAspectRatio:true,
    elements:{
      point:{
        pointStyle:'circle',
        radius:8,
      },
    },
    scales:{
      x:{
        // type:'timeseries',
        // time:{
        //   unit:'day',
        // },
        // adapters:{
        //   date:{
        //     locale:enIN
        //   }
        // },
        title:{
          display:true,
          color:'#000000',
          font:{
            size:16,
            weight:500,
            family:'Roboto',
          }
        },
        ticks:{
          source:'labels',
          font:{
            weight:(c)=>{
              const currentDate = new Date(c["tick"].value)
              const todaysDate = new Date();
              if(
                (currentDate.getDate() === todaysDate.getDate()) && 
                (currentDate.getMonth() === todaysDate.getMonth()) &&
                (currentDate.getFullYear() === todaysDate.getFullYear())
                )
                {
                  return 'bold';
                }
                
              return 'normal';
            },
          }
        }
      },
      y:{
        title:{
          display:true,
          text:'Quantity',
          align:'center',
          color:'#000000',
          font:{
            size:18,
            weight:300,
            family:'Roboto'
          }
          
        },
        beginAtZero:true,
        ticks:{
          stepSize:50,
        },
      }
    },
    plugins:{
      legend:{
        labels:{
          usePointStyle:true,
        },
        onClick(e, legendItem, legend) {
          const index:any = legendItem.datasetIndex;
          const ci = legend.chart;
          if (ci.isDatasetVisible(index)) {
              ci.hide(index);
              legendItem.hidden = true;
          } else {
              ci.show(index);
              legendItem.hidden = false;
          }
        },
        position:'bottom'
      },
      tooltip:{
        intersect:true,
        enabled:false,
        external:customTooltip,
        position:'nearest',
      }
    }
  }

  const chartRef = useRef<ChartJS>();
  const [visibleDataSets,setVisibleDataSets] = useState<number[]>(()=>{
    return chartData.datasets.map((_:any,index:number)=>index);
  });

  useEffect(()=>{
    if(chartRef.current){
      if(visibleDataSets.length === 0){
        chartData.datasets.forEach((data:ChartData,dataSetIndex:number)=>{
            chartRef.current?.show(dataSetIndex);
        })
      }
      else{
        chartData.datasets.forEach((data:ChartData,dataSetIndex:number)=>{
          if(visibleDataSets.includes(dataSetIndex)){
            chartRef.current?.show(dataSetIndex);
          }
          else{
            chartRef.current?.hide(dataSetIndex);
          }
        })
      }
    }
    
    
  },[visibleDataSets])


  const onToggleDataset = (e:any) => {
    const dataSetIndex = chartData.datasets.findIndex((d:ChartDataset)=>d.label === e.target.name);
    if(e.target.value === "0"){
      setVisibleDataSets([...visibleDataSets,dataSetIndex])
    }
    else{
      setVisibleDataSets(visibleDataSets.filter((visibleDataSetIndex:number)=>visibleDataSetIndex !== dataSetIndex));
    }
  }



    return(
        <VFModalCard openModal={isModalOpen} closeModal={closeModal} headerIcon='' headerText="Seasonality Graph" headerBgColor="white" headerTextColor="#000000" paddingLeftAndRight={27} closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}>
            <SCSeasonalityContainer>
                <SCChartContainer>
                    <Chart type="bar" data={chartData} options={chartOptions} ref={chartRef}/>
                </SCChartContainer>
                <SCSeasonalityStatusDetails>
                  <SCSeasonalityDetailsTitle themeUi={theme_ui}>
                    Seasonality Status Details
                  </SCSeasonalityDetailsTitle>
                  <SCSeasonalityDetailsBody>
                    <SCText fontWeight={500} fontSize={16}>Select Type :</SCText>
                    <SCCheckBoxRow>
                      <SCCheckBoxContainer>
                        <Checkbox name="BuildUpDuration" value={"BuildUpDuration"} onChange={onToggleDataset} defaultChecked={true} data-testid="checkbox" />
                        <SCText fontWeight={300} fontSize={16}>Build Up Duration</SCText>
                      </SCCheckBoxContainer>
                      <SCCheckBoxContainer>
                        <Checkbox name="GIT" value={"GIT"} onChange={onToggleDataset} defaultChecked={true} data-testid="checkbox" />
                        <SCText fontWeight={300} fontSize={16}>GIT</SCText>
                      </SCCheckBoxContainer>
                    </SCCheckBoxRow>
                    <SCCheckBoxRow>
                      <SCCheckBoxContainer>
                        <Checkbox name="Stock" value={"Stock"} onChange={onToggleDataset} defaultChecked={true} data-testid="checkbox" />
                        <SCText fontWeight={300} fontSize={16}>Stock</SCText>
                      </SCCheckBoxContainer>
                    </SCCheckBoxRow>
                    <SCHorizontalDivider/>
                    <SCDataRow>
                      <SCDataNode>
                        <SCText fontWeight={300} fontSize={16}>SKU Code:</SCText>
                        <SCText fontWeight={500} fontSize={18}>{rowData.sc}</SCText>
                      </SCDataNode>
                      <SCVerticalDivider/>
                      <SCDataNode>
                        <SCText fontWeight={300} fontSize={16}>SKU Name:</SCText>
                        <SCText fontWeight={500} fontSize={18}>{rowData.skd}</SCText>
                      </SCDataNode>
                    </SCDataRow>
                    <SCHorizontalDivider/>
                    <SCDataRow>
                      <SCDataNode>
                        <SCText fontWeight={300} fontSize={16}>Location Code:</SCText>
                        <SCText fontWeight={500} fontSize={18}>{rowData.wc}</SCText>
                      </SCDataNode>
                      <SCVerticalDivider/>
                      <SCDataNode>
                        <SCText fontWeight={300} fontSize={16}>Location Name:</SCText>
                        <SCText fontWeight={500} fontSize={18}>{rowData.wd}</SCText>
                      </SCDataNode>
                    </SCDataRow>
                    <SCHorizontalDivider/>
                    <SCDataRow>
                      <SCDataNode>
                        <SCText fontWeight={300} fontSize={16}>Season Start Date</SCText>
                        <SCText fontWeight={500} fontSize={18}>{rowData.sd}</SCText>
                      </SCDataNode>
                      <SCVerticalDivider/>
                      <SCDataNode>
                        <SCText fontWeight={300} fontSize={16}>Season End Date</SCText>
                        <SCText fontWeight={500} fontSize={18}>{rowData.ed}</SCText>
                      </SCDataNode>
                    </SCDataRow>
                    <SCHorizontalDivider/>
                    <SCDataRow>
                      <SCDataNode>
                        <SCText fontWeight={300} fontSize={16}>Original Norm</SCText>
                        <SCText fontWeight={500} fontSize={18}>{rowData.onm}</SCText>
                      </SCDataNode>
                      <SCVerticalDivider/>
                      <SCDataNode>
                        <SCText fontWeight={300} fontSize={16}>Target Norm</SCText>
                        <SCText fontWeight={500} fontSize={18}>{rowData.tn}</SCText>
                      </SCDataNode>
                    </SCDataRow>
                    <SCHorizontalDivider/>
                    <SCDataRow>
                      <SCDataNode>
                        <SCText fontWeight={300} fontSize={16}>Build Up Duration</SCText>
                        <SCText fontWeight={500} fontSize={18}>{rowData.bd}</SCText>
                      </SCDataNode>
                      <SCVerticalDivider/>
                      <SCDataNode>
                        <SCText fontWeight={300} fontSize={16}>RLT</SCText>
                        <SCText fontWeight={500} fontSize={18}>{rowData.r}</SCText>
                      </SCDataNode>
                    </SCDataRow>

                    
                  </SCSeasonalityDetailsBody>           
                </SCSeasonalityStatusDetails>
            </SCSeasonalityContainer>
        </VFModalCard>
    )


}

export default SeasonalityChartModal;