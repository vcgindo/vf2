import React, {useEffect, useState} from 'react'
import RadioSelect from '../../../../../components/VectorFLOW/commons/MTO/RadioSelect'
import { FOLIcon, StepGroup, StepperWrapper } from './RouteAssignment.styled'
import _ from 'lodash'

interface IRouteAssignmentProps {
    theme: string,
    ccrGroupMaster?: any,
    selectedRoutes?: any,
    setSelectedRoutes?: any,
    isEditable?: boolean,
    onChange?: (route:any) => void,
    isCCRGroupEditable?: boolean,
}

const RouteAssignment = ({theme, ccrGroupMaster=[], selectedRoutes, setSelectedRoutes, isEditable = true, isCCRGroupEditable= false}: IRouteAssignmentProps) => {
  const [sortedSelectedRoutes, setSortedSelectedRoutes] = useState<any>([]);
  useEffect(() => {
        const adjustLayout = (containerWidth: number, items: any) => {
          let currWidth = 0;
          let lineType = true;
          let array: any = [];
          let myIndex = 1;
  
          items.forEach((element: any) => {
            
              if (currWidth + element.offsetWidth + 35  > containerWidth) {
              if (!lineType) array.reverse();
      
              array.forEach((e: any) => {
                e.style.order = myIndex++;
                e.dataset.order = lineType ? "asc" : "dsc";
              });
      
              array = [element];
              currWidth = element.offsetWidth + 35;
              lineType = !lineType;
            } else {
              array.push(element);
              currWidth += element.offsetWidth + 35;
            }
          });
      
          if (!lineType) array.reverse();
      
          array.forEach((e: any) => {
            e.style.order = myIndex++;
            e.dataset.order = lineType ? "asc" : "dsc";
          });

        };
      
        const drawLines = () => {
          const stepGroups: any = document.querySelectorAll('.route-assignment .step-group');
          const svg: any = document.querySelector('.line');
          const stepperWrapper: any = document.querySelector('.route-assignment');
          if (stepGroups && stepperWrapper && svg) {
              const stepperRect = stepperWrapper.getBoundingClientRect();
              adjustLayout(stepperWrapper.offsetWidth, stepGroups);
              
              svg.innerHTML = "";
              for (let i = 0; i < stepGroups.length -1; i++) {
              const start: any = stepGroups[i].getBoundingClientRect();
              const end: any = stepGroups[i + 1].getBoundingClientRect();
              const stepDot = 5.2;

      
              const adjustedStart = {
                y: start.top - stepperRect.top,
                x: start.right - stepperRect.left + stepDot ,
                height: start.height,
              };
              const adjustedEnd = {
                y: end.top - stepperRect.top,
                x: end.left - stepperRect.left - stepDot  ,
                height: end.height,
                width: end.width ,
              };

      
              const currentOrder = stepGroups[i].dataset.order;
              const nextOrder = stepGroups[i + 1].dataset.order;
      
              if (currentOrder === "asc" && nextOrder === "dsc") {
                adjustedEnd.x = end.right - stepperRect.left + stepDot;

              } else if (currentOrder === "dsc" && nextOrder === "dsc") {
                adjustedStart.x = start.left - stepperRect.left - stepDot;
                adjustedEnd.x = end.right - stepperRect.left + stepDot;
              } else if (currentOrder === "dsc" && nextOrder === "asc") {
                adjustedStart.x = start.left - stepperRect.left - stepDot;
                adjustedEnd.x = end.left - stepperRect.left - stepDot;
              }
      
              // Polyline for inactive
              if (stepGroups[i + 1].id === "inactive") {
                const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
                polyline.setAttribute(
                  "points",
                  `${adjustedEnd.x - 8},${adjustedEnd.y + adjustedEnd.height / 2 - 2.5} ${adjustedEnd.x - 8},${adjustedEnd.y - 10} ${adjustedEnd.x + 8 + adjustedEnd.width},${adjustedEnd.y - 10} ${adjustedEnd.x + 8 + adjustedEnd.width},${adjustedEnd.y + adjustedEnd.height / 2 - 2.5}`
                );
                polyline.setAttribute("stroke", "#82104C"); 
                polyline.setAttribute("fill", "none");
                svg.appendChild(polyline);
              }
      
              // Line connection
              const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
              const leftOffset = stepGroups[i + 1].id === "inactive" ? 5 : 0;
              const rightOffset = stepGroups[i].id === "inactive" ? 5 : 0;
      
              line.setAttribute("x1", (adjustedStart.x + rightOffset).toString());
              line.setAttribute("y1", (adjustedStart.y + adjustedStart.height / 2 - 1).toString());
              line.setAttribute("x2", (adjustedEnd.x - leftOffset).toString());
              line.setAttribute("y2", (adjustedEnd.y + adjustedEnd.height / 2 - 1).toString());
              line.setAttribute("stroke", "#82104C");
              svg.appendChild(line);
            }
          }
        };
      
        drawLines(); // initial call
      
        window.addEventListener("resize", drawLines);
        return () => {
          window.removeEventListener("resize", drawLines);
        };
      }, [sortedSelectedRoutes]);
      

    useEffect(()=>{
        if(selectedRoutes && ccrGroupMaster){

            const val = _.cloneDeep(selectedRoutes);
            setSortedSelectedRoutes(val.map((routeGroup: any) => {
                const [ccrGroup, ccr] = routeGroup;
                const sortedCcrs = ccrGroup.ccrs.sort((a: any, b: any) => a.fol - b.fol);
                return [{ ...ccrGroup, ccrs: sortedCcrs }, ccr];
            }))
            
        }

    },[selectedRoutes, ccrGroupMaster])
    
  
  useEffect(() => {
    if (isEditable && ccrGroupMaster && ccrGroupMaster.length == 1) {
      if (!selectedRoutes.length) {
        setSelectedRoutes(new Array([ccrGroupMaster[0], null]));
      }
    }
  }, [isEditable]);
  
  //if one ccrgroup is already selected then dont show that group for selection in another dropdown route assignment
  const updateOption = (ccrGroupMaster: any, selectedRoute: any) => {
    if (!sortedSelectedRoutes || !sortedSelectedRoutes.length) {
      return ccrGroupMaster;
    }

    const ccrGroupCopy = _.cloneDeep(ccrGroupMaster);

    const selectedCCRGroupValues = sortedSelectedRoutes.map((route: any) => route[0].value);

    return ccrGroupCopy.filter((ccrGroup: any) =>
      !selectedCCRGroupValues.includes(ccrGroup.value) || ccrGroup.value === selectedRoute?.value
    );
   
  }
    
  return (
    <StepperWrapper
      ccrMasterLength={ccrGroupMaster.length}
      key="route-assignment"
      className="route-assignment">
      {
        ccrGroupMaster.length ? (
          ccrGroupMaster.map((ccrGroup: any, index: number) => {
            return (
              <StepGroup $step={true} key={`route-assignment-${index}`}>
                <RadioSelect
                  key={`route-assignment-${index}-${1}`}
                  isDisabled={!isCCRGroupEditable || !isEditable}
                  theme={theme}
                  color="lightgrey"
                  options={updateOption(ccrGroupMaster,sortedSelectedRoutes?.[index]?.[0])}
                  isClearable
                  value={sortedSelectedRoutes?.[index]?.[0] || null}
                  onChange={(newValue: any) => {
                    const newGroups = [...sortedSelectedRoutes];
                    if (newValue == null || newValue == undefined) {
                      newGroups[index] = null
                    } else {
                      newGroups[index] = [newValue, null];
                    }
                    setSelectedRoutes(newGroups.filter(item => item !== undefined && item !== null));
                  }}
                />
                <RadioSelect
                  key={`route-assignment-${index}-${2}`}
                  isClearable
                  isDisabled={!isEditable}
                  theme={theme}
                  value={sortedSelectedRoutes[index]?.[1] || null}
                  options={sortedSelectedRoutes[index]?.[0]?.ccrs.filter((ccr: any) => ccrGroupMaster.some((group: any) => group.ccrs.some((c: any) => c.value === ccr.value)))}
                  onChange={(newValue: any) => {
                    const newGroups = [...sortedSelectedRoutes];
                    newGroups[index][1] = newValue;
                    setSelectedRoutes(newGroups);
                  }}
                  Icon={(props: any) => {
                    const data = props.props.data;
                    const color = data.fol === data.minFol ? "green" : "red";
                    return <div style={{ color: color, display: "flex", alignItems: "center", gap: "5px" }}><FOLIcon width={(data.fol / data.maxFol) * 100} color={color} /><span>[{data.fol}]</span></div>
                  }}
                />
              </StepGroup>
            )
          })
        ) : (<span>No CCR's available for selected item type.</span>)
      }
        
        {/* <StepGroup $step={true}>
            <RadioSelect theme={theme} selected={ccrGroupMaster[0]} color="lightgrey" options={ccrGroupMaster}/>
            <RadioSelect theme={theme} selected={{}}/>
        </StepGroup>
        <StepGroup $step={true}>
            <RadioSelect theme={theme} selected={ccrGroupMaster[0]} color="lightgrey" options={ccrGroupMaster}/>
            <RadioSelect theme={theme} selected={{ }}/>
        </StepGroup>
        <StepGroup $step={true}>
            <RadioSelect theme={theme} selected={ccrGroupMaster[0]} color="lightgrey" options={ccrGroupMaster}/>
            <RadioSelect theme={theme} selected={{ }}/>
        </StepGroup>
        <StepGroup id="inactive" $step={true}>
            <RadioSelect theme={theme} selected={ccrGroupMaster[0]} color="lightgrey" options={ccrGroupMaster}/>
            <RadioSelect theme={theme}/>
        </StepGroup>
        <StepGroup $step={true}>
            <StepLabel>Final Product</StepLabel>
        </StepGroup> */}
            <svg className="line" style={{ position: "absolute", width: "100%", height: "100%", top: "0", left: "0", pointerEvents: "none" }}>
            </svg>
        </StepperWrapper>
    )
}

export default React.memo(RouteAssignment)