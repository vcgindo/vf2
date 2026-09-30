import { GridOptions, SideBarDef } from 'ag-grid-enterprise'
import { format } from 'date-fns'
import React, { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
// import { useUpdateScheduleOrders } from '../../../../../VectorFlow/Services/MTO/Production/DueDateQuotation';
import Radio from '../../../../../components/VectorFLOW/commons/MTO/Radio'
import VFTable from '../../Common/VFTable';
import { Arrow, BasketingContainer, BasketingLabel, BasketingLabelText, BasketingSection, DateRange, DateRangeLabel } from './DueDateQuotation.styled'
import { notifyError, notifySuccess } from '../../../../../helpers/notify';
import * as globalStyles from "../../../../../styles/global";
import { getColumnDefinations } from '../../../../../helpers/utils';

enum SchedulingType {
    ItemLevel,
    Basket
}

const Step3 = forwardRef(({ columnData, gridOptions, confirmedRows, setConfirmedRows, theme, WorkingCalender, setStep, setDisabled, setSelectedRows, setMasters, updateScheduleOrders, columnState, setCurrentPage }: any, ref: any) => {
    
    useEffect(()=>{
        setDisabled(true);
    }, [])

    const customization = {
        OrderID: {
            cellRenderer: "agGroupCellRenderer"
        },
        CRDD: {
            pinned: "right",
            lockPosition: true,
            minWidth: 120,
            cellStyle: {
                // background: "#BC3D814F",
                // color: "#BC3D81",
                color: globalStyles.chooseThemeColor[theme]?.color4,
                fontWeight: "bold"
            }
        },
        EstimatedDD: {
            pinned: "right",
            lockPosition: true,
            minWidth: 120,
            cellStyle: {
                // background: "#BC3D814F",
                // color: "#BC3D81",
                color: globalStyles.chooseThemeColor[theme]?.color4,
                fontWeight: "bold"
            }
        },
    }

    const extras: any = [
        {
            field: "",
            headerCheckboxSelection: true,
            checkboxSelection: true,
            suppressMenu: true,
            maxWidth: 50,
            position: 0,
            filter: false,
            colId: "checkbox",
            pinned: 'left',
        }
    ]


    const columnDefs = useMemo(() => {
        return getColumnDefinations(columnData || [], customization, extras);
    }, []);

    const options: GridOptions = {
        ...gridOptions,
        columnDefs: columnDefs,
    }




    const [dates, setDates] = useState<any>();
    const [schedulingType, setSchedulingType] = useState(SchedulingType.ItemLevel);
    const gridRef = useRef<any>();
    // const { mutateAsync: updateScheduleOrders, isLoading: isUpdateScheduleOrders } = useUpdateScheduleOrders();

    const calculateReleaseDateAndPostOrderBuffer = (maxDateLno: any, dueDateLno: any, schedulingType: any, order: any) => {
        let ddLno: any;
        let postOrderBuffer = 0;
        if (schedulingType === SchedulingType.ItemLevel) {
            ddLno = dueDateLno;
        }
        else if (schedulingType === SchedulingType.Basket) {
            ddLno = maxDateLno;
            postOrderBuffer = maxDateLno - dueDateLno;
        }
        const prodBuffer = order.prSz || 0;
        const procBuffer = order.pcSz || 0;
        // console.log("procBuffer: Step3",procBuffer);
        // const releaseDateLno = ddLno - prodBuffer - procBuffer - postOrderBuffer + 1;
        const releaseDateLno = ddLno - prodBuffer- postOrderBuffer + 1;
        const releaseDate = WorkingCalender.find((data: any) => {
            return data.ccrId == order.maxFolSpan.ccr_id && data.PlId == order.plid && data.lno == releaseDateLno;
        })?.wd;

        return [releaseDate, postOrderBuffer]
    }

    const onScheduled = async () => {
        try {
            const selected = gridRef.current.api.getSelectedRows();
            const obj: any = [];
            const scheduled = new Set();
            selected.forEach((order: any) => {
                const [releaseDate, postOrderBuffer] = calculateReleaseDateAndPostOrderBuffer(dates.maxDateLno, order.dueDateLno, schedulingType, order);
                obj.push({
                    ok: order.ok,
                    dd: schedulingType === SchedulingType.Basket ? dates.maxDate : order.cdd,
                    rd: releaseDate,
                    pobsz: postOrderBuffer
                })
                scheduled.add(order.ok);
            });
            await updateScheduleOrders({ orders: obj });

            // const newScheduledOrders = new Set([...scheduledOrders])
            const newConfirmedRows = confirmedRows.filter((row: any) => {
                return !scheduled.has(row.ok);
            })

            
            if(newConfirmedRows.length == 0){
                setCurrentPage(1); //afetr scheduling all orders from step3, getting redirected to step 1 then the current page needs to be reset to 1 else NAN issue occurs
                setStep(1);
                setConfirmedRows(null);
                setSelectedRows(new Map());
                setMasters(null);
            }else{
                setConfirmedRows(newConfirmedRows);
            }
            // setScheduledOrders(newScheduledOrders);
            notifySuccess("Orders Scheduled Successfully")
        }
        catch (err) {
            console.log(err);
            notifyError("Something went wrong!")
        }


    }

    useImperativeHandle(ref, () => ({
        onScheduled: onScheduled
    }));

    const sideBar = React.useMemo<SideBarDef | string | string[] | boolean | null >(() => {
    return {
      toolPanels: [
        {
          id: "columns",
          labelDefault: "Columns",
          labelKey: "columns",
          iconKey: "columns",
          toolPanel: "agColumnsToolPanel",
          toolPanelParams: {
            suppressPivots: true,
            suppressPivotMode: true,
          },
        },
      ],
    };
  }, []);

    const isBasketDisabled = confirmedRows?.length == 1;


    return (
        <>
            <VFTable
                containerStyle={{ padding: "1rem" }}
                key="scheduling"
                ref={gridRef}
                gridOptions={options}
                rowData={confirmedRows}
                onGridReady={(params)=>{
                    params.api.selectAll();
                    if (columnState) {
                        params.api.applyColumnState({
                            state: [...columnState],
                            applyOrder: true
                        });
                    }
                }}
                onRowSelected={(params: any) => {
                    const selected = params.api.getSelectedRows()
                    if (selected.length === 0) {
                        setDates(null);
                        setDisabled(true)
                        return
                    }
                    setDisabled(false)
                    let minDate: any = new Date(confirmedRows[0].cdd);
                    let minDateLno: any = confirmedRows[0].dueDateLno;
                    let maxDate: any = new Date(confirmedRows[0].cdd);
                    let maxDateLno: any = confirmedRows[0].dueDateLno;
                    selected.forEach((order: any) => {
                        minDate = new Date(Math.min(new Date(order.cdd) as any, minDate));
                        minDateLno = Math.min(order.dueDateLno, minDateLno);
                        maxDate = new Date(Math.max(new Date(order.cdd) as any, maxDate));
                        maxDateLno = Math.max(order.dueDateLno, maxDateLno)
                    });
                    minDate = format(minDate, "yyyy-MM-dd");
                    maxDate = format(maxDate, "yyyy-MM-dd");
                    setDates({
                        minDate,
                        minDateLno,
                        maxDate,
                        maxDateLno
                    });
                }}
                sideBar={sideBar}
                maintainColumnOrder
            />
            {dates && <BasketingSection>
                <BasketingContainer>
                    <BasketingLabel>
                        <BasketingLabel style={{ width: "45%" }}>
                            <Radio theme={theme} name="scheduling_type" onClick={() => setSchedulingType(SchedulingType.ItemLevel)} checked={schedulingType === SchedulingType.ItemLevel ? true : false} />
                            <BasketingLabelText theme={theme}>
                                <svg xmlns="http://www.w3.org/2000/svg" width="13.594" height="12.949" viewBox="0 0 13.594 12.949">
                                    <path id="package" d="M46.1,3.126,39.67.041a.43.43,0,0,0-.365,0L32.873,3.126a.3.3,0,0,0-.183.263V9.56a.3.3,0,0,0,.183.263L39.3,12.909a.43.43,0,0,0,.365,0L46.1,9.823a.3.3,0,0,0,.183-.263V3.389a.3.3,0,0,0-.183-.263Zm-6.615,3L37,4.932,42.7,2.2l2.485,1.192Zm0-5.47,2.485,1.192-5.7,2.735L33.786,3.389ZM33.421,3.915l2.487,1.193V7.953a.372.372,0,0,0,.731,0V5.458L39.122,6.65v5.47l-5.7-2.735Zm6.432,8.205V6.65l5.7-2.735v5.47Z" transform="translate(-32.69 0)" />
                                </svg>
                                Item Level Scheduling
                            </BasketingLabelText>
                        </BasketingLabel>
                        {dates && <DateRange>
                            <DateRangeLabel>Date Range</DateRangeLabel>
                            <div style={{ background: "lightgrey", borderRadius: "4px", padding: '0.25rem' }}>
                                {dates?.minDate}
                            </div>
                            <Arrow />
                            <div style={{ background: "lightgrey", borderRadius: "4px", padding: '0.25rem' }}>
                                {dates?.maxDate}
                            </div>
                        </DateRange>
                        }

                    </BasketingLabel>
                    <BasketingLabel>
                        <BasketingLabel style={{ width: "45%", opacity:isBasketDisabled?0.5:1 }}>
                            <Radio theme={theme} name="scheduling_type" onClick={() => setSchedulingType(SchedulingType.Basket)} checked={schedulingType === SchedulingType.Basket ? true : false} disabled={confirmedRows?.length == 1}/>
                            <BasketingLabelText theme={theme}>
                                <svg id="Group_5077" data-name="Group 5077" xmlns="http://www.w3.org/2000/svg" width="16.325" height="15.049" viewBox="0 0 16.325 15.049">
                                    <path id="Path_11099" data-name="Path 11099" d="M120.325,222.5v-.813a1.257,1.257,0,0,0-1.289-1.22h-3.165l-1.586-4.2a.437.437,0,0,0-.549-.246.4.4,0,0,0-.26.52l1.483,3.93h-5.593l1.483-3.93a.4.4,0,0,0-.26-.52.437.437,0,0,0-.549.246l-1.586,4.2h-3.165a1.257,1.257,0,0,0-1.289,1.22v.813a1.233,1.233,0,0,0,.916,1.168l1,5.674a2.111,2.111,0,0,0,2.119,1.7h8.258a2.111,2.111,0,0,0,2.119-1.7s-.131,1.285.119-.134.88-5.54.88-5.54a1.233,1.233,0,0,0,.916-1.168Zm-15.466-.813a.419.419,0,0,1,.43-.407h2.858l-.255.677a.4.4,0,0,0,.26.52.437.437,0,0,0,.549-.246l.358-.95h6.207l.358.95a.429.429,0,0,0,.4.27.411.411,0,0,0,.4-.544l-.255-.677h2.858a.419.419,0,0,1,.43.407v.813a.419.419,0,0,1-.43.407H105.289a.419.419,0,0,1-.43-.407Zm12.7,7.522a1.266,1.266,0,0,1-1.271,1.02h-8.258a1.266,1.266,0,0,1-1.271-1.02l-.966-5.488h12.733Z" transform="translate(-104 -215.997)" />
                                    <path id="Path_11100" data-name="Path 11100" d="M248.366,388.386a.366.366,0,0,0,.366-.366v-3.655a.366.366,0,0,0-.731,0v3.655A.366.366,0,0,0,248.366,388.386Z" transform="translate(-240.203 -374.8)" />
                                    <path id="Path_11101" data-name="Path 11101" d="M304.329,388.384a.365.365,0,0,0,.4-.327l.366-3.655a.366.366,0,0,0-.727-.073L304,387.984A.365.365,0,0,0,304.329,388.384Z" transform="translate(-293.122 -374.799)" />
                                    <path id="Path_11102" data-name="Path 11102" d="M184.367,388.056a.366.366,0,0,0,.727-.073l-.366-3.655a.366.366,0,0,0-.727.073Z" transform="translate(-179.649 -374.798)" />
                                </svg>
                                Basket Level Scheduling
                            </BasketingLabelText>
                        </BasketingLabel>
                        {dates && <DateRange>
                            <DateRangeLabel>Basket Date</DateRangeLabel>
                            <div style={{ background: "lightgrey", borderRadius: "4px", padding: '0.25rem' }}>
                                {dates?.maxDate}
                            </div>
                        </DateRange>
                        }

                    </BasketingLabel>
                </BasketingContainer>
            </BasketingSection>}
            
        </>
    )
})
export default Step3