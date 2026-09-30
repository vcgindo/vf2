import { AgCharts } from 'ag-charts-react';
import { GridOptions, SideBarDef } from 'ag-grid-enterprise';
import { Allotment } from 'allotment';
import React, { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import { getColumnDefinations } from '../../../../../helpers/utils';
import VFTable from '../../Common/VFTable';
import BufferAssignment from '../../Common/RouteAssignment/BufferAssignment';
import RouteAssignment from '../../Common/RouteAssignment/RouteAssignment';
import { WarningBody, WarningContainer, WarningHeader, WarningText, Wrapper } from './DueDateQuotation.styled';
import { BlurCover, CardCover, DashedCard, MessageText } from '../EnquiryResponse/styles';
import VFButtonOutline from '../../../../../components/VectorFLOW/commons/VFButtonOutline';
import { useGetRouteDetails, useUpdateBuffRouteCCREstDate } from '../../../../../VectorFlow/Services/MTO/Production/DueDateQuotation';
import VFButton from '../../../../../components/VectorFLOW/commons/VFButton';
import _ from 'lodash';
import { add, addDays, format, max } from 'date-fns';
import Tooltip from '../../Common/Tooltip';
import { notifyError, notifyErrorWithoutAutoClose, notifySuccess } from '../../../../../helpers/notify';
import * as globalStyles from "../../../../../styles/global";
import { useUserData } from '../../../../../context';
import VFToolTip from '../../../../../components/VectorFLOW/commons/MTO/VFToolTip';

const Step2 = forwardRef(({ gridOptions, columnData, selectedRows, theme, masters, getMastersData, rowsSelectedForAssignment, setRowsSelectedForAssignment, confirmedRows, setConfirmedRows, lineCCR, setDisabled, columnState }: any, ref) => {
    useEffect(() => {
        getMastersData();
        setRowsSelectedForAssignment(false);
    }, []);

    const user = useUserData()
    const canChangeRoute =user?.user?.feature_permission?.includes('Change_Route');
    useEffect(() => {
        if (masters) {
            if (confirmedRows) {
                setRows(confirmedRows.map((row: any) => {
                    return row
                }))
            }
            else {
                const arr = Array.from(selectedRows.values()).map((node: any) => {
                    if (node.data.rid) {
                        routeLookup.current.set(node.data.rn, node.data.rid);
                    }
                    // calculate leadtime 
                    // if (node.data.cdd) {
                    //     const marketLeadTime = masters.MarketLeadTimeMaster.find((item: any) => {
                    //         return item.mbot === node.data.mbot && item.itid === node.data.itid;
                    //     });

                    //     if (marketLeadTime) {
                    //         const today = new Date();
                    //         today.setHours(0, 0, 0, 0);
                    //         const newDate = add(today, {
                    //             years: 0,
                    //             months: 0,
                    //             weeks: 0,
                    //             days: marketLeadTime.lt || 0,
                    //             hours: 0,
                    //             minutes: 0,
                    //             seconds: 0,
                    //         });
                    //         const cdd = new Date(node.data.cdd);
                    //         node.data.isOptimalLeadTime = cdd <= newDate;
                    //     }
                    // }
                    return { ...node.data }
                });

                arr.sort((a, b) => {
                    // Compare by 'crdd' first
                    const aCrdd = new Date(a.cedd);
                    const bCrdd = new Date(b.cedd);

                    if (aCrdd < bCrdd) return -1;
                    if (aCrdd > bCrdd) return 1;



                    const aOrderIdNum = parseInt(a.oid.replace(/\D/g, ''));
                    const bOrderIdNum = parseInt(b.oid.replace(/\D/g, ''));

                    // If 'crdd' is equal, compare by 'orderId'
                    if (aOrderIdNum < bOrderIdNum) return -1;
                    if (aOrderIdNum > bOrderIdNum) return 1;

                    return 0;  // equal values
                });

                calculateEstimatedDueDate(arr).then((data) => {
                    setRows(data);
                })

            }
        }
    }, [lineCCR])

    const routeDiv = useRef<any>();
    // const [routeDivHeight, setRouteDivHeight] = useState<any>();

    useEffect(() => {
        setTimeout(() => {
            allotment.current.reset();
            // if (routeDiv.current?.offsetHeight)
            // setRouteDivHeight(routeDiv.current.offsetHeight);
        }, 0);
        //RouteDiv Position Calculate and move it to state instead of ref
    }, [rowsSelectedForAssignment])

    //     useEffect(() => {
    //         allotment.current.reset();
    //     //RouteDiv Position Calculate and move it to state instead of ref
    //   }, [routeDivHeight])



    const customization = {
        OrderID: {
            cellRenderer: "agGroupCellRenderer",
            cellStyle: {
                minWidth: "30px",
            }
        },
        Route: {
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
        ProductionBuffer: {
            pinned: "right",
            lockPosition: true,
            minWidth: 100,
            cellStyle: {
                // background: "#BC3D814F",
                // color: "#BC3D81",
                color: globalStyles.chooseThemeColor[theme]?.color4,
                fontWeight: "bold"
            }
        },
        ProcurementBuffer: {
            pinned: "right",
            lockPosition: true,
            minWidth: 100,
            cellStyle: {
                // background: "#BC3D814F",
                // color: "#BC3D81",
                color: globalStyles.chooseThemeColor[theme]?.color4,
                fontWeight: "bold"
            }
        },
        CRDD: {
            pinned: "right",
            lockPosition: true,
            minWidth: 140,
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
            minWidth: 140,
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
            maxWidth: 35,
            position: 0,
            filter: false,
            colId: "checkbox",
            pinned: 'left',
        },
        {
            field: "",
            minWidth: 30,
            maxWidth: 30,
            cellRenderer: (params: any) => {
                if (params.data.isOptimalLeadTime == undefined) {
                    return
                }
                return (
                    <div style={{ height: "100%", display: "flex", alignItems: "center" }}>
                        <Tooltip content={<div style={{ padding: "1rem", maxWidth: "180px", textAlign: "center", fontSize: "14px" }}>{params.data.isOptimalLeadTime ? "Optimal Lead Time" : "Exceeding market operating leadtime"}</div>} zoom={false} style={{ display: "flex" }}>
                            {params.data.isOptimalLeadTime ?
                                <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 17.326 16.976">
                                    <g id="Component_237_99" data-name="Component 237 – 99" transform="translate(1.202 1.162)">
                                        <g id="Icon_feather-check-circle" data-name="Icon feather-check-circle" transform="translate(-3 -2.991)">
                                            <path id="Path_13420" data-name="Path 13420" d="M17.71,9.674v.677a7.355,7.355,0,1,1-4.362-6.722" transform="translate(0 0)" fill="none" stroke="#418d18" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
                                            <path id="Path_13421" data-name="Path 13421" d="M23.061,6l-7.355,7.362L13.5,11.156" transform="translate(-5.352 -1.534)" fill="none" stroke="#418d18" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
                                        </g>
                                    </g>
                                </svg>
                                : <svg id="Icon_metro-warning" data-name="Icon metro-warning" xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 20 20">
                                    <path id="Icon_metro-warning-2" data-name="Icon metro-warning" d="M12.571,3.74l8.381,16.7H4.19l8.381-16.7Zm0-1.812a1.446,1.446,0,0,0-1.189.872L2.845,19.814c-.654,1.163-.1,2.114,1.236,2.114H21.06c1.334,0,1.89-.951,1.236-2.114h0L13.76,2.8A1.445,1.445,0,0,0,12.571,1.928Zm1.25,16.25a1.25,1.25,0,1,1-1.25-1.25A1.25,1.25,0,0,1,13.821,18.178Zm-1.25-2.5a1.25,1.25,0,0,1-1.25-1.25v-3.75a1.25,1.25,0,0,1,2.5,0v3.75A1.25,1.25,0,0,1,12.571,15.678Z" transform="translate(-2.571 -1.928)" fill="#ff3636" />
                                </svg>}
                        </Tooltip>
                    </div>

                )
            },
            suppressMenu: true,
            position: 1,
            filter: false
        },
    ]


    const columnDefs = useMemo(() => {
        return getColumnDefinations(columnData || [], customization, extras);
    }, []);

    const options: GridOptions = {
        ...gridOptions,
        columnDefs: columnDefs,
        // tooltipTrigger:"focus",
        // getRowStyle:(params: any) => null
    }


    const [chartData, setChartData] = useState<any>([]);
    const [maxFolinDays, setMaxFolInDays] = useState(1);

    const interval = useMemo(() => {
        let i = 2
        if (maxFolinDays > 30) {
            i = Math.floor(maxFolinDays / 5)
        }
        return i
    }, [maxFolinDays])

    const barColors = {
        "ccrFolWithHoliday": "black",
        "orderLoad": "#3874FF",
        "fol_gap": "#FF8A00"
    }

    const tooltipValues = (value: any) => {
        return `${value} ${value == 1 ? " day" : " days"}`
    }

    function TooltipRenderer({ datum, xKey }: any) {
        return `
        <div style="background:#6C696A; style="transform: translateX(120px)" >
        <div  style=" color: white; padding: 10px 10px 4px;background-color: #6C696A; display: flex; justify-content: center; align-items: center; border-bottom: 1px dashed white">
            ${datum[xKey]}
        </div>
        <div style="color: white; background-color: #6C696A; padding: 10px;">
          <div style="display: flex; align-items: center;">
            <div style="margin-right: 10px; height: 3px; width: 15px; background-color: ${barColors["ccrFolWithHoliday"]}"></div>
            FOL with holidays: ${tooltipValues(datum["ccrFolWithHoliday"])} (FOL- ${tooltipValues(datum["FOL"])}, Holidays- ${tooltipValues(datum["holidays"])} )
          </div>
          <div style="display: flex; align-items: center;">
            <div style="margin-right: 10px; height: 3px; width: 15px; background-color: ${barColors["orderLoad"]}"></div>
            SOL: ${tooltipValues(datum["orderLoad"])}
          </div>
        </div>
        </div>`;
    
        // dont remove below code require for fol gap phase 2
        {/*<div style="display: flex; align-items: center;">
            <div style="margin-right: 10px; height: 3px; width: 15px; background-color: ${barColors["fol_gap"]}"></div>
            FOL Gap: ${tooltipValues(datum["fol_gap"])}
          </div>*/}
      }

    const chartOptions: any = {
        data: chartData,
        tooltip: {
            mode: "single",
        },
        series: [
            {
                type: "bar",
                direction: "horizontal",
                xKey: "ccr_name",
                yKey: "ccrFolWithHoliday",
                yName: "FOL",
                stacked: true,
                fill: barColors["ccrFolWithHoliday"],
                tooltip: {
                    position: { placement: "right" },  // anchor to bar
                    renderer: TooltipRenderer
                }
            },
            // {
            //     type: "bar",
            //     direction: "horizontal",
            //     xKey: "ccr_name",
            //     yKey: "fol_gap",
            //     yName: "FOL Gap",
            //     stacked: true,
            //     fill: barColors["fol_gap"],
            //     tooltip: {
            //         position: { placement: "right" },  // anchor to bar
            //         renderer: TooltipRenderer
            //     }
            // },
            {
                type: "bar",
                direction: "horizontal",
                xKey: "ccr_name",
                yKey: "orderLoad",
                yName: "SOL",
                stacked: true,
                fill: barColors["orderLoad"],
                tooltip: {
                    position: { placement: "right" },  // anchor to bar
                    renderer: TooltipRenderer
                }
            },
        ],
        axes: [
            {
                type: "category",
                position: "left",
                label: {
                    fontSize: 10,
                    color: "black",
                    padding: 10,
                },
                gridLine: {
                    enabled: false,
                },
            },
            {
                type: "number",
                position: "bottom",
                line: { enabled: true },
                interval: { step: interval },
                tick: {
                    enabled: true,
                },
                label: {
                    fontSize: 10,
                    color: "black",
                    formatter: labelFormatter,
                    rotation: -45,
                    avoidCollisions: true
                },
                gridLine: {
                    enabled: false,
                },
            },
        ],

        legend: {
            position: 'right',
            item: {
                label: {
                    fontSize: 10,
                },
            },
        },
    };


    // const rows = useMemo(()=> selectedRows.values().map((node: any) => node.data), [])   
    const routeLookup = useRef(new Map());
    const [rows, setRows] = useState<any>(null);
    const [newSelectedRows, setNewSelectedRows] = useState<any>({ rows: null, isAssignmentPossible: false });
    const [selectedRoute, setSelectedRoute] = useState<any>([]);

    const [selectedPlant, setSelectedPlant] = useState<number | null>(null);

    // console.log(masters);

    const allotment = useRef<any>();
    const gridRef = useRef<any>();
    const [selectedBuffers, setSelectedBuffers] = useState<any[]>([]);
    const [isEditable, setIsEditable] = useState(false);

    const { mutateAsync: getRouteDetails, } = useGetRouteDetails();
    const { mutateAsync: updateBuffRouteCCREstDate, } = useUpdateBuffRouteCCREstDate();
    const routeCache = useRef<Record<number, any>>({});
    const [no, setNo] = useState(false);
    const [arePlantsDifferent, setArePlantsDifferent] = useState(false);

    // Look up for CCRItemTypeMappingMaster
    const CCRItemTypeMappingMasterLookup = useMemo(() => {
        const mappingLookup = new Map<string, Set<string>>();
        if (masters?.CCRItemTypeMappingMaster) {
            masters.CCRItemTypeMappingMaster.forEach((mapping: { ccrId: string, it: string }) => {
                if (!mappingLookup.has(mapping.ccrId)) {
                    mappingLookup.set(mapping.ccrId, new Set());
                }
                mappingLookup.get(mapping.ccrId)?.add(mapping.it);
            });
        }
        return mappingLookup
    }, [masters?.CCRItemTypeMappingMaster])

    // console.log("selectedPlant", selectedPlant)
    // console.log("ccrGroups", ccrGroups)
    // console.log("master", masters)

    const getRoute = async (route: any) => {
        try {
            if (typeof route === "number") {
                if (routeCache.current[route]) {
                    return _.cloneDeep(routeCache.current[route])
                }
                const data = await getRouteDetails(route);
                const routeDetails = data.data.data;
                routeDetails.sort((a: any, b: any) => a.ps - b.ps)
                const newRoute: any = []
                routeDetails.forEach((routeDetail: any) => {
                    const obj = []
                    const ccrGroup = masters.ccrGroups.find((ccr: any) => ccr.value === routeDetail.ccrGrpId);
                    obj[0] = ccrGroup;
                    obj[1] = ccrGroup.ccrs.find((ccr: any) => ccr.value === routeDetail.ccrId)
                    newRoute[routeDetail.ps - 1] = obj
                })
                routeCache.current[route] = newRoute;
                return _.cloneDeep(newRoute)
            }
            return JSON.parse(route)
        }
        catch (err) {
            console.error(err);
            notifyError("Something Went Wrong!");
        }
    }

    const getBuffer = (prod_buffer: any, proc_buffer: any) => {
        try {
            const buffer = [null, null];
            if (prod_buffer.length == 1) {
                const prodBuff = masters.prodMaster.find((prod: any) => prod.value === prod_buffer[0]);
                buffer[0] = prodBuff
            }
            if (proc_buffer.length == 1) {
                const procBuff = masters.procMaster.find((proc: any) => proc.value === proc_buffer[0]);
                buffer[1] = procBuff
            }
            return buffer
        }
        catch (err) {
            console.error(err);
            notifyError("Something Went Wrong!");
        }
    }

    const calculateEstimatedDueDate = async (rowData: any) => {
        try {
            const ccr_prev_pending: any = {};
            const ordersForDDQ = [...rowData]
            // console.log("rowData", ordersForDDQ)
            const promises = ordersForDDQ.map(async (order: any) => {
                if (order.prodc && order.rn) {
                    const order_ccr_data: any = {};

                    const ccrIds: any = [];
                    const ccrNames: any = [];

                    //TODO: if the New Route Does not exist, use the rid --done
                    let route;

                    if (order.newRoute) {
                        route = order.newRoute
                    } else {
                        route = await getRoute(order.rid);
                    }


                    route.forEach((r: any) => {
                        if (r[1]?.value) {
                            ccrIds.push(r[1].value)
                            ccrNames.push(r[1].label)
                        }
                    });


                    //calculating order load
                    const errors: any = []
                    ccrIds.forEach((ccrId: any, index: number) => {
                        const ccr = masters.CCRMaster.find((ccr: any) => {
                            return ccr.ccr_id === ccrId
                        })
                        // const fol = masters.FOL[ccrId];
                        const ccrItem = masters?.CCRItemTypeMappingMaster.find((ccr: any) => ccr.ccrId === ccrId && ccr.it == order.itid)

                        if (!ccrItem) {
                            errors.push(`CCR Name: ${ccrNames[index]} not available in MapCCRItemType Master`)
                            // throw new Error(`CCR Name: ${ccrNames[index]} not available in MapCCRItemType Master`)
                        }
                        if (!ccrItem?.tt) {
                            errors.push(`Touch Time not available for CCR Name: ${ccrNames[index]} and Item ID: ${order.itid} in MapCCRItemType Master`)
                            // throw new Error(`Touch Time not available for CCR Name: ${ccrNames[index]} and Item ID: ${order.itid} in MapCCRItemType Master`);
                        }
                        const ccrWorkingHoursPerDay = ccr.working_hours_per_day;
                        // ccrWorkingHoursPerDay = parseInt(ccrWorkingHoursPerDay);
                        // console.log("ccritem", ccrItem)
                        // console.log("lineCCR[order.ok]?.[ccrId]?.pcqty", lineCCR[order.ok]?.[ccrId]?.pcqty)
                        // console.log("order.pcqty", order.pcQty)

                        const lineCCRPendingQty = lineCCR[order.ok]?.[ccrId]?.pcqty || 0;
                        const orderPendingCCRQty = order.pcqty || 0;

                        if (lineCCRPendingQty !== null && lineCCRPendingQty < 0 && lineCCRPendingQty === undefined) {
                            if (!orderPendingCCRQty) {
                                errors.push(`Missing Pending Qty for CCR: ${ccrNames[index]} for Order: ${order.oid}`)
                            }
                        }

                        const orderLoad = Math.ceil(((ccrItem?.tt || 0) * (lineCCRPendingQty && lineCCRPendingQty >= 0 ? lineCCRPendingQty : orderPendingCCRQty)));
                    
                        //for calculating the initial value for prevPending
                        if (!ccr_prev_pending[ccrId]) {
                            const ccr_fol_data = masters.FOL[ccrId];
                            const folInDays = ccr_fol_data?.fol ?? -1;
                            const ocm = ccr_fol_data?.ocm ?? -1;
                            // console.log("folInDays", folInDays)
                            // console.log("ocm", ocm)
                            if (folInDays == -1 || ocm == -1) {
                                errors.push(`"FOL" or "Occupied Quanitity In Muniutes (OCM)" missing for CCR Name: ${ccrNames[index]}`)
                            }
                            // console.log("ccr_fol_data",ccr_fol_data)
                            // console.log("ccrWorkingHoursPerDay", ccrWorkingHoursPerDay)
                            // console.log("folInDays", folInDays)
                            // console.log("prev pending",  Math.ceil((folInDays * ccrWorkingHoursPerDay * 60) + ccr_fol_data.ocm))

                            ccr_prev_pending[ccrId] = {
                                ccr_id: ccrId,
                                prevPend: Math.ceil((folInDays * ccrWorkingHoursPerDay * 60) + ocm)
                            }
                        }
                        ccr_prev_pending[ccrId].prevPend = (ccr_prev_pending[ccrId].prevPend) + orderLoad;

                        order_ccr_data[ccrId] = {
                            ccr_id: ccrId,
                            ccr_name: ccrNames[index],
                            ccrgrp: ccr?.ccr_group,
                            orderLoad: orderLoad || 0,
                            pos: index + 1,
                            pcQty: lineCCRPendingQty || orderPendingCCRQty,
                            folSpan: ((ccr_prev_pending[ccrId].prevPend)) / (ccrWorkingHoursPerDay * 60),
                        }

                        // console.log(ccrId, "orderLoad", order_ccr_data[ccrId].orderLoad, "folSpan" ,order_ccr_data[ccrId].folSpan, "order pending qty",row.pcqty, "ccr tt", ccrItem.tt, "ccrWorkingHoursPerDay" ,ccrWorkingHoursPerDay)                     
                    });
                    if (errors.length > 0) {
                        throw new Error(errors.join("\n\n"))
                    }

                    order.CCRData = _.cloneDeep(order_ccr_data);





                    //DDIndex
                    const maxFolSpan: any = Object.values(order_ccr_data).reduce((prev: any, current: any) => (current.folSpan > prev.folSpan) ? current : prev);

                  
                    // const formattedDate = format(new Date(), 'yyyy-MM-dd');
                    const today = new Date();
                    today.setHours(0, 0, 0, 0);

                    // console.log()

                    const latestWorkingDayLno = masters.WorkingCalender.find((data: any) => {
                        return new Date(data.wd) >= today && data.ccrId == maxFolSpan.ccr_id && data.PlId == order.plid
                    })?.lno;

                    if (!latestWorkingDayLno) {
                        throw new Error(`Working calender missing for CCR ${maxFolSpan.ccr_name} and Plant ${order.pn}`)
                    }

                    const residualBuffer = parseFloat(masters?.CCRMaster.find((ccr: any) => ccr.ccr_id == maxFolSpan.ccr_id)?.residual_buffer);
                    if (residualBuffer == undefined || residualBuffer == null) {
                        throw new Error(`Residual Missing for CCR: ${maxFolSpan.ccr_name}`)
                    }

                    const prodBufferSize = order.prSz || 0;
                    const procBufferSize = order.pcSz || 0;

                    //optimise the logic
                    const folDDIndex = Math.ceil(latestWorkingDayLno + maxFolSpan.folSpan + (residualBuffer * prodBufferSize)) - 1;
                    const folDD = masters.WorkingCalender.find((data: any) => {
                        return data.lno == folDDIndex && data.ccrId == maxFolSpan.ccr_id && data.PlId == order.plid
                    })?.wd;

                    const bufferDDIndex = latestWorkingDayLno + procBufferSize + prodBufferSize;
                    const bufferDD = masters.WorkingCalender.find((data: any) => {
                        return data.lno == bufferDDIndex && data.ccrId == maxFolSpan.ccr_id && data.PlId == order.plid
                    })?.wd;


                    const crDD = order.cedd;
                    const crDDIndex = masters.WorkingCalender.find((data: any) => {
                        return data.ccrId == maxFolSpan.ccr_id && data.PlId == order.plid && new Date(data.wd) >= new Date(crDD)
                    })?.lno || -Infinity;


                    const crddFlag = masters.DBRSettings.find((setting: any) => setting.flag == "ConsiderCRDDInDDQ");
                  
                    // const crddFlag = 0;
                    let maxDate;

                    if (crddFlag?.value == 1) {
                        maxDate = max([folDD, bufferDD, crDD]);
                    } else {
                        maxDate = max([folDD, bufferDD]);
                    }


                    order.cdd = format(maxDate, 'yyyy-MM-dd');
                    order.dueDateLno = Math.max(folDDIndex, bufferDDIndex, crDDIndex);
                    order.maxFolSpan = maxFolSpan;

                    // console.log("maxDate", format(maxDate, 'yyyy-MM-dd'));
                    const marketLeadTime = masters.MarketLeadTimeMaster.find((item: any) => {
                        return item.mbot === order.mbot && item.itid === order.itid;
                    });

                    if (marketLeadTime) {
                        // const optimalLeadTime = 
                        const newDate = add(today, {
                            days: marketLeadTime.lt || 0,
                        })
                        order.isOptimalLeadTime = maxDate <= newDate;
                        // console.log(marketLeadTime);
                    }
                }
                return order
            });

            await Promise.all(promises);

            return ordersForDDQ
        }
        catch (err: any) {
            console.error(err);
            // notifyError("Something Went Wrong!");
            notifyErrorWithoutAutoClose(<div style={{ whiteSpace: "pre-line" }}>{err.message}</div>);
            if (rows)
                setRows([...rows])
            setSelectedBuffers([])
            setSelectedRoute([])
            setRowsSelectedForAssignment(false);
        }
    }


    const onSave = () => {
        try {
            if (isEditable) {
                const selectedOrders = new Set(gridRef.current.api.getSelectedRows().map((row: any) => row.ok));
                const formattedRoute = formatRoute(selectedRoute);
                const prodBuffer = selectedBuffers[0];
                const procBuffer = selectedBuffers[1];

                const newRows = rows.map((row: any) => {
                    const newRow = _.cloneDeep(row)
                    if (selectedOrders.has(row.ok)) {
                        //update the routes in all the orders
                        newRow.rn = formattedRoute;
                        newRow.newRoute = selectedRoute;
                        //update the buffers in all the orders
                        newRow.nprid = prodBuffer?.value
                        newRow.npcid = procBuffer?.value

                        newRow.prodc = prodBuffer?.label
                        newRow.procc = procBuffer?.label

                        newRow.prSz = prodBuffer?.size;
                        newRow.pcSz = procBuffer?.size;

                        newRow.updated = true;
                    }
                    return newRow
                });

                calculateEstimatedDueDate(newRows).then((data) => {
                    if (data) {
                        setRows(data);
                        setSelectedBuffers([])
                        setSelectedRoute([])
                        setRowsSelectedForAssignment(false);
                    }
                })



            }
            setIsEditable(!isEditable);
        }
        catch (err) {
            console.error(err);
            notifyError("Something Went Wrong!");
        }
    }

    const onReset = () => {
        try {
            //TODO: move this to a common logic 
            const arr = Array.from(selectedRows.values()).map((node: any) => {
                if (node.data.rid) {
                    routeLookup.current.set(node.data.rn, node.data.rid);
                }
                // calculate leadtime 
                if (node.data.cdd) {
                    const marketLeadTime = masters.MarketLeadTimeMaster.find((item: any) => {
                        return item.mbot === node.data.mbot && item.itid === node.data.itid;
                    });

                    if (marketLeadTime) {
                        const today = new Date();
                        today.setHours(0, 0, 0, 0);
                        const newDate = add(today, {
                            years: 0,
                            months: 0,
                            weeks: 0,
                            days: marketLeadTime.lt || 0,
                            hours: 0,
                            minutes: 0,
                            seconds: 0,
                        });
                        const cdd = new Date(node.data.cdd);
                        node.data.isOptimalLeadTime = cdd <= newDate;
                    }
                }
                return { ...node.data }
            });

            arr.sort((a, b) => {
                // Compare by 'crdd' first
                const aCrdd = new Date(a.cedd);
                const bCrdd = new Date(b.cedd);

                if (aCrdd < bCrdd) return -1;
                if (aCrdd > bCrdd) return 1;



                const aOrderIdNum = parseInt(a.oid.replace(/\D/g, ''));
                const bOrderIdNum = parseInt(b.oid.replace(/\D/g, ''));

                // If 'crdd' is equal, compare by 'orderId'
                if (aOrderIdNum < bOrderIdNum) return -1;
                if (aOrderIdNum > bOrderIdNum) return 1;

                return 0;  // equal values
            });
            setRows(arr);
            setSelectedBuffers([])
            setSelectedRoute([])
            setRowsSelectedForAssignment(false);
        }
        catch (err) {
            console.error(err);
            notifyError("Something Went Wrong!");
        }
    }


    const formatRoute = (route: any) => {
        try {
            let formattedRoute: any = []
            route.forEach((route: any) => {
                if (route[1]?.label) {
                    formattedRoute.push(route[1]?.label);
                }
            })
            formattedRoute = formattedRoute.join("/");
            return formattedRoute
        }
        catch (err) {
            console.error(err);
            notifyError("Something Went Wrong!");
        }

    }

    const loadGraph = (selectedRoute: any) => {
        try {
            const ccrIds: any = [];
            selectedRoute.forEach((route: any) => {
                if (route?.[1])
                    ccrIds.push(route[1]?.value);
            })

            const orderLoadOfCCRs: any = {}

            let maxFol = 0
            newSelectedRows?.rows?.forEach((order: any) => {

                ccrIds.forEach((ccrId: any) => {
                    const ccr = masters.CCRMaster.find((ccr: any) => {
                        return ccr.ccr_id === ccrId
                    })
                    const ccrWorkingHoursPerDay = ccr.working_hours_per_day || "1";
                    // ccrWorkingHoursPerDay = parseInt(ccrWorkingHoursPerDay);

                    const ccrItemTypeMapping = masters?.CCRItemTypeMappingMaster.find((ccr: any) => ccr.ccrId === ccrId && ccr.it == order.itid)
                    // console.log(JSON.parse(JSON.stringify(orderLoadOfCcrs)))

                    const orderLoadInDays = ((orderLoadOfCCRs[ccrId]?.orderLoad || 0) * 1.0) + ((ccrItemTypeMapping?.tt || 1) * order.pcqty) / (ccrWorkingHoursPerDay * 60);

                    const ccrFolInDays = masters.FOL[ccrId]?.fol;
                    
                    const today: any = new Date();
                    today.setHours(0, 0, 0, 0);

                    // TODO: Check if plant id is also to be matched
                    const latestWorkingDayLno = masters.WorkingCalender.find((data: any) => {
                        return new Date(data.wd) >= today && data.ccrId == ccrId && data.PlId == order.plid
                        // return new Date(data.wd) >= today && data.ccrId == ccrId
                    })?.lno;
                    
                    const folIndex = Math.ceil(latestWorkingDayLno + ccrFolInDays - 1);
                    const maxFOLIndex = Math.max(latestWorkingDayLno, folIndex);
                    const folDD: any = masters.WorkingCalender.find((data: any) => {
                        return data.lno == maxFOLIndex && data.ccrId == ccrId && data.PlId == order.plid
                    })?.wd;
                    const formatedFOLDate = new Date(folDD);
                    formatedFOLDate.setHours(0, 0, 0, 0);

                    let diffDays: any = dateDiffInDays(today, formatedFOLDate);

                    // Added - 1 only if the dates are different for graph to consider todays date in graph
                    if (diffDays !== 0) {
                        diffDays += 1;
                    }
                    
                    const FOLGap = masters.FOL[ccrId]?.fol_gap || 0;

                    maxFol = Math.max(diffDays, maxFol, FOLGap);

                    orderLoadOfCCRs[ccrId] = {
                        ccrId,
                        ccr_name: ccr.ccr_name,
                        orderLoad: orderLoadInDays,
                        ccrFolWithHoliday: diffDays,
                        fol_gap: FOLGap,
                        FOL: ccrFolInDays,
                        holidays: diffDays - Math.ceil(ccrFolInDays),
                    }
                })
            });

            // console.log(JSON.parse(JSON.stringify(orderLoadOfCCRs)))

            setMaxFolInDays(maxFol)

            setChartData(Object.values(orderLoadOfCCRs).map((order: any) => {
                return { ...order, orderLoad: Math.ceil(order.orderLoad) }
            }))

        }
        catch (err) {
            console.error(err);
            notifyError("Something Went Wrong!");
        }
    }

    const deselectAllForStep2 = () => {
        gridRef.current.api.deselectAll();
        allotment.current.reset()
    }

    // Label formatter function
    function labelFormatter(params: any) {
        try {            
            const today = new Date();

            today.setDate(today.getDate() - 1); // should consider todays also in graph so -1 added
            
            const value = parseInt(params.value);

            if (value == 0) {
                return format(today, "dd MMM yy");  // Returns today's date
            } else if (value > 0) {
                // const futureDate = addDays(today, value);
                const futureDate = add(today, { days: value });
                // console.log(value,futureDate)
                return format(futureDate, "dd MMM yy");  // Returns future date
            }
        }
        catch (err) {
            console.error(err);
            notifyError("Something Went Wrong!");
        }
    }

    function dateDiffInDays(date1: any, date2: any) {
        //if fol date is not valid then return date diff as 0
        if (!(date1 instanceof Date) || isNaN(date1.getTime()) ||
            !(date2 instanceof Date) || isNaN(date2.getTime())) {
            return 0;
        }

        // One day in milliseconds
        const oneDay = 1000 * 60 * 60 * 24;

        // Convert both dates to milliseconds
        const date1Ms = date1.getTime();
        const date2Ms = date2.getTime();

        // Calculate the difference in milliseconds
        const diffMs = Math.abs(date1Ms - date2Ms);

        // Convert back to days and return
        return Math.round(diffMs / oneDay);
    }

    useEffect(() => {
        loadGraph(selectedRoute);

    }, [selectedRoute])

    useEffect(() => {
        const filteredRows = rows?.filter((row: any) => {
            return row.prodc && ((row.rn != null && row.rn !=="") || row?.newRoute?.length) ? false : true
        }) || [];
        setDisabled(filteredRows.length != 0)
    }, [rows])

    const onConfirm = async () => {
        try {
            const bufferAssignmentObj: any = [];
            const routeAssignmentObj: any = [];
            rows.forEach((row: any) => {
                if (row.updated) {
                    bufferAssignmentObj.push({
                        ok: row.ok,
                        prod_id: row.nprid,
                        proc_id: row.npcid,
                        estdd: row.cdd,
                        ccr: row.maxFolSpan.ccr_id
                    })
                    routeAssignmentObj.push({
                        route: row.rn,
                        ok: row.ok,
                        ccrdetails: Object.values(row.CCRData).map((ccr: any) => {
                            const temp = _.cloneDeep(ccr);
                            temp.ccrid = ccr.ccr_id;
                            temp.ol = ccr.orderLoad
                            delete temp["ccr_id"];
                            delete temp["folSpan"];
                            delete temp["orderLoad"];
                            return temp;
                        })
                    })
                }
            })
         
            if (bufferAssignmentObj.length != 0 && routeAssignmentObj.length != 0) { //TODO: check if this is a OR condition or AND condition
                const data = await updateBuffRouteCCREstDate({ bufferData: { ordData: bufferAssignmentObj }, routeData: { orders: routeAssignmentObj } });
                notifySuccess(data.data.msg)
            }
            setConfirmedRows(rows);
            return true
        }
        catch (err) {
            console.log(err)
            notifyError("Route & Buffer Assignment Failed!");
            return false
        }

    }

    useImperativeHandle(ref, () => ({
        onConfirm: onConfirm,
        deselectAllForStep2: deselectAllForStep2
    }));

    const [countOfExceedingLeadTime, countOfTotalExceedingLeadTime] = useMemo(() => {
        const current = rows?.filter((row: any) => {
            return row.isOptimalLeadTime === false
        }).length || 0;
        const total = rows?.length || 0;
        return [current, total]
    }, [rows, newSelectedRows?.rows])


    const isSaveDisabled = useMemo(() => {
        const isDisabled = selectedRoute.some((route: any) => {
            return !route[0] || !route[1];
        });
        return isDisabled;
    }, [selectedRoute, selectedBuffers])

    const sideBar = React.useMemo<
        SideBarDef | string | string[] | boolean | null
    >(() => {
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

    //ccr groups & ccrs filter on the basis of plant
    const calculateCCGroups = () => {
        const itemTypes: Set<string> = new Set()
        if (newSelectedRows?.rows?.length) {
            newSelectedRows.rows.forEach((row: any) => {
                if (row?.itid)
                    itemTypes.add(row.itid);
            })
        }
        
        if (selectedPlant && masters && itemTypes.size > 0) {
            // Get all CCRs for each item type
            const ccrSets = Array.from(itemTypes).map(itemType => {
                const ccrSet = new Set<string>();
                masters?.CCRItemTypeMappingMaster.forEach((mapping: any) => {
                    if (mapping.it === itemType) {
                        ccrSet.add(mapping.ccrId);
                    }
                });
                return ccrSet;
            });

            // Check if all item types have the same CCRs
            const allCCRsMatch = ccrSets.every((ccrSet, _, arr) => {
                const firstSet = arr[0];
                return ccrSet.size === firstSet.size && Array.from(ccrSet).every(value => firstSet.has(value));
            });

            if (allCCRsMatch) {
                // If all item types have the same CCRs, use the first item type's CCRs
                const firstItemType = Array.from(itemTypes)[0];
                return masters?.ccrGroups.map((ccrGroup: any) => {
                    return {
                        ...ccrGroup, 
                        ccrs: ccrGroup.ccrs.filter((ccr: any) => {
                            return ccr.plant_id == selectedPlant && CCRItemTypeMappingMasterLookup.get(ccr.value)?.has(firstItemType);
                        })
                    }
                })?.filter((ccrGroup: any) => ccrGroup.ccrs.length != 0)
            }
        }
        
        // Fallback to plant-based filtering if CCRs don't match or no item types
        if (selectedPlant && masters) {
            return masters?.ccrGroups.map((ccrGroup: any) => {
                return {
                    ...ccrGroup, 
                    ccrs: ccrGroup.ccrs.filter((ccr: any) => {
                        return ccr.plant_id == selectedPlant;
                    })
                }
            })?.filter((ccrGroup: any) => ccrGroup.ccrs.length != 0)
        }
        
        return []
    }
    
 
    const ccrGroups = useMemo(calculateCCGroups, [masters, selectedPlant, newSelectedRows])

    return (
        <>
            <Allotment vertical separator ref={allotment} snap={false} proportionalLayout={false}>
                <Allotment.Pane preferredSize={rowsSelectedForAssignment ? "30%" : '50%'} key={1}>
                    <Wrapper style={{ margin: 0 }}>
                        <VFTable
                            key="selectedRows"
                            ref={gridRef}
                            tooltipShowDelay={0}
                            gridOptions={options}
                            columnDefs={options.columnDefs}
                            rowData={rows}
                            onSelectionChanged={async (params: any) => {
                                try {

                                    setIsEditable(false);
                                    setNo(false)
                                    const selected = params.api.getSelectedRows();
                                    if (selected.length) {
                                        setRowsSelectedForAssignment(true);
                                    } else {
                                        setSelectedBuffers([])
                                        setSelectedRoute([])
                                        setRowsSelectedForAssignment(false);
                                        setArePlantsDifferent(false)
                                        return
                                    }
                                    const selectedRoutes: any = new Set();
                                    const selectedProdBuffer: any = new Set();
                                    const selectedProcBuffer: any = new Set();
                                    const selectedPlants: any = new Set();
                                    const selectedItemTypes: any = new Set();


                                    selected.forEach((row: any) => {
                                        if (row.plid) {
                                            selectedPlants.add(row.plid)
                                        }
                                        if (row.itid) {
                                            selectedItemTypes.add(row.itid);
                                        }
                                        if (row.newRoute) {
                                            const formattedRoute = formatRoute(row.newRoute);
                                            if (routeLookup.current.get(formattedRoute)) {
                                                selectedRoutes.add(routeLookup.current.get(formattedRoute));
                                            } else {
                                                selectedRoutes.add(JSON.stringify(row.newRoute));
                                            }
                                        }
                                        else if (row.rid) {
                                            selectedRoutes.add(row.rid);
                                        }
                                        else {
                                            selectedRoutes.add(null);
                                        }

                                        if ("nprid" in row) {
                                            selectedProdBuffer.add(row.nprid);
                                        }
                                        else if (row.prid) {
                                            selectedProdBuffer.add(row.prid);
                                        }
                                        else {
                                            selectedProdBuffer.add(null)
                                        }
                                        if ("npcid" in row) {
                                            selectedProcBuffer.add(row.npcid);
                                        }
                                        else if (row.pcid) {
                                            selectedProcBuffer.add(row.pcid);
                                        }
                                        else {
                                            selectedProcBuffer.add(null)
                                        }
                                    });

                                    // if (selectedItemTypes.size > 1) {

                                    // }

                                    let isAssignmentPossible = true; //if only one order is selected
                                    if (selected.length > 1) {
                                        isAssignmentPossible = ([1].includes(selectedRoutes.size)) && ([1].includes(selectedProdBuffer.size)) && ([1].includes(selectedProcBuffer.size))
                                    }
                                    if (selectedPlants.size == 1 && selectedItemTypes.size == 1) {
                                        setArePlantsDifferent(false)
                                        setSelectedPlant([...selectedPlants][0])
                                    } 
                                    else if(selectedPlants.size==1 && selectedItemTypes.size>1){
                                        const itemTypeArray = Array.from(selectedItemTypes);
                                        const ccrSets = itemTypeArray.map((itemType) => {
                                            const ccrSet = new Set<string>();
                                            masters?.CCRItemTypeMappingMaster.forEach((mapping: any) => {
                                                if (mapping.it === itemType) {
                                                    ccrSet.add(mapping.ccrId);
                                                }
                                            });
                                            return ccrSet;
                                        });
                                        const allCCRsMatch = ccrSets.every((ccrSet, _, arr) => {
                                            const firstSet = arr[0];
                                            return ccrSet.size === firstSet.size && Array.from(ccrSet).every(value => firstSet.has(value));
                                        });


                                        if (!allCCRsMatch) {
                                            isAssignmentPossible = false;
                                            setSelectedPlant(null)
                                            setArePlantsDifferent(true)
                                        }
                                        else{
                                            setArePlantsDifferent(false)
                                            setSelectedPlant([...selectedPlants][0])
                                        }

                                        // setArePlantsDifferent(false)
                                        // setSelectedPlant([...selectedPlants][0])
                                    }
                                    else {
                                        
                                        isAssignmentPossible = false;
                                        setSelectedPlant(null)
                                        setArePlantsDifferent(true)
                                    }
                                    const routeId = [...selectedRoutes][0]
                                    if (selectedRoutes.size == 0) {
                                        setSelectedRoute([])
                                    }
                                    else if (selectedRoutes.size == 1 && routeId != null) {
                                        const routeDetails = await getRoute(routeId);
                                        setSelectedRoute(routeDetails);
                                    }
                                    // TODO: check this condition -> check for null
                                    const prod = [...selectedProdBuffer]
                                    const proc = [...selectedProcBuffer]
                                    if (((selectedProdBuffer.size == 1 && prod[0] != null) || (selectedProcBuffer.size == 1 && proc[0] != null))) {
                                        const buffer: any = getBuffer(prod, proc);
                                        setSelectedBuffers(buffer)
                                    }
                                    if (!isAssignmentPossible) {
                                        setSelectedBuffers([])
                                        setSelectedRoute([])
                                    }
                                    setNewSelectedRows({ rows: selected, isAssignmentPossible});
                                }
                                catch (err) {
                                    console.error(err);
                                    notifyError("Something Went Wrong!");
                                }
                            }}
                            onColumnPinned={(params: any) => {
                                params.api?.autoSizeAllColumns();
                            }}
                            onGridReady={(params: any) => {
                                params.api.autoSizeAllColumns();
                                if (columnState) {
                                    params.api.applyColumnState({
                                        state: [...columnState],
                                        applyOrder: true
                                    });
                                }
                            }}
                            sideBar={sideBar}
                            maintainColumnOrder
                        />
                    </Wrapper>
                </Allotment.Pane>
                {rowsSelectedForAssignment &&
                    <Allotment.Pane
                        // preferredSize={routeDivHeight - 50} 
                        preferredSize={210}
                        key={2}
                    >
                        <Wrapper style={{ margin: 0, filter: newSelectedRows.isAssignmentPossible ? "unset" : "blur(3px)" }} >
                            <div ref={routeDiv} style={{ height: "100%", background: "white", boxShadow: "rgba(0, 0, 0, 0.1) 0px 2px 10px 2px", margin: "20px 10px", padding: "1rem", position: "relative", overflow: "visible" }}>
                                <div style={{ display: "flex", position: "absolute", right: "1rem", gap: "0.5rem" }}>
                                 <div className="disabled-button-wrapper">
                                    <VFButton
                                        themeUi={theme}
                                        onClick={onSave}
                                        // disabled={isEditable ? isSaveDisabled : false}
                                        disabled={!canChangeRoute || (isEditable && isSaveDisabled)}
                                            
                                        style={{ fontSize: "10px", width: "60px", height: "20px", padding: "0 1rem", display: "flex", justifyContent: "center", alignItems: "center", gap: "1rem" }}>
                                        {isEditable ? <> <img src="/assets/img/mto/dueDateQuotation/save-icon.svg" />Save</> : <> <img src="/assets/img/mto/dueDateQuotation/edit-icon.svg" /> Edit</>}
                                        </VFButton>

                                        {!canChangeRoute && (
                                            <VFToolTip
                                                text={'The logged-in user does not have access to edit the routes.'}
                                            /> 
                                            )}
                                    </div>
                                    
                             
                                    <div className="disabled-button-wrapper">
                                        <VFButtonOutline
                                        themeUi={theme}
                                        onClick={onReset}
                                        disabled={!canChangeRoute} 
                                        style={{
                                        fontSize: '10px',
                                        width: '60px',
                                        height: '20px',
                                        padding: '0 1rem',
                                        display: 'flex',
                                        justifyContent: 'center',
                                        alignItems: 'center',
                                        gap: '0.5rem',
                                        }}
                                    >
                                        <img src="/assets/img/mto/dueDateQuotation/reset-icon.svg" style={{opacity: !canChangeRoute ? 0.4 : 1}} />
                                        Reset
                                        </VFButtonOutline>
                                        {!canChangeRoute && (
                                        <VFToolTip
                                            text={'The logged-in user does not have access to reset the routes.'}
                                        />
                                    )}
                                    </div>

                                    
                                </div>
                                <div style={{ display: "flex", gap: "2rem" }}>
                                    <div style={{ flex: "2" }}>
                                        <h3 style={{ margin: "1rem 0" }}>Route Assignment</h3>
                                        <RouteAssignment
                                            isEditable={isEditable}
                                            theme={theme}
                                            ccrGroupMaster={ccrGroups}
                                            selectedRoutes={selectedRoute}
                                            setSelectedRoutes={setSelectedRoute}
                                            isCCRGroupEditable = {true}
                                        />
                                    </div>
                                    <div style={{ flex: "1" }}>
                                        <h3 style={{ margin: "1rem 0" }}>Buffer Assignment</h3>
                                        <BufferAssignment
                                            isEditable={isEditable}
                                            theme={theme}
                                            bufferMaster={masters}
                                            selectedBuffers={selectedBuffers}
                                            setSelectedBuffers={setSelectedBuffers}
                                        />
                                    </div>
                                </div>
                            </div>
                        </Wrapper>
                        {!newSelectedRows.isAssignmentPossible &&
                            <BlurCover style={{ borderRadius: "0", left: 0, width: "100%" }}>
                                <CardCover>
                                    <DashedCard style={{ width: "500px" }}>
                                        <MessageText style={{ textAlign: "center", display: "flex", flexDirection: "column", width: "100%", gap: "2rem" }}>
                                            {arePlantsDifferent ? <div>Selected orders have different plants or ccrs assigned therefore they cannot be modified together.</div> : !no ? <>
                                                <div>
                                                    Selected orders have different routes and buffer.<br />
                                                    Do you want to edit these orders together?
                                                </div>
                                                <div style={{ display: "flex", gap: "1rem", justifyContent: "center" }}>
                                                    <VFButtonOutline
                                                        themeUi={theme}
                                                        onClick={() => {
                                                            setNewSelectedRows({ ...newSelectedRows, isAssignmentPossible: true })
                                                            setSelectedBuffers([])
                                                            setSelectedRoute([])
                                                        }}
                                                    >
                                                        Yes
                                                    </VFButtonOutline>
                                                    <VFButtonOutline themeUi={theme} onClick={() => { setNo(true) }}>No</VFButtonOutline>
                                                </div></> :
                                                <div>Selected orders have different route and buffer.</div>
                                            }
                                        </MessageText>
                                    </DashedCard>
                                </CardCover>
                            </BlurCover>
                        }

                    </Allotment.Pane>
                }
                {rowsSelectedForAssignment &&
                    <Allotment.Pane preferredSize={'33%'} key={3}>
                        <Wrapper style={{ padding: "20px 0 10px 0", margin: 0, paddingBottom: "75px" }}>
                            <div style={{ height: "100%", overflow: "visible", display: "flex", width: "100%" }}>
                                <div style={{ display: 'flex', flexDirection: "column", width: countOfExceedingLeadTime != 0 ? "80%" : "100%", background: "white", boxShadow: "rgba(0, 0, 0, 0.1) 0px 2px 10px 2px", margin: "0 1rem 1rem 1rem" }}>
                                    <h3 style={{ margin: "1rem", borderBottom: "1px dashed black" }}>CCR Load Chart</h3>
                                    <AgCharts options={chartOptions} />
                                </div>
                                {countOfExceedingLeadTime != 0 && <div style={{ width: "20%", margin: "0 1rem" }}>
                                    <WarningContainer>
                                        <WarningHeader >
                                            <img src="/assets/img/mto/dueDateQuotation/warning-outlined.svg" /> <h3 style={{ margin: 0, marginLeft: "1rem" }}>Warning!</h3>
                                        </WarningHeader>
                                        <WarningBody>
                                            <WarningText>
                                                Calculated due dates in {countOfExceedingLeadTime}/{countOfTotalExceedingLeadTime} are exceeding the market operating lead time
                                            </WarningText>
                                        </WarningBody>
                                    </WarningContainer>
                                </div>}

                            </div>
                        </Wrapper>
                    </Allotment.Pane>
                }
                {!rowsSelectedForAssignment &&
                    <Allotment.Pane preferredSize={"50%"} key={4}>
                        <Wrapper style={{ justifyContent: "center", alignItems: "center", background: "white", margin: "20px 10px", height: "calc(100% - 30px)", color: "grey", boxShadow: "rgba(0, 0, 0, 0.1) 0px 2px 10px 2px", overflow: "visible" }}>
                            <div style={{ fontSize: "16px" }}>No Data to Display</div>
                            <div style={{ fontSize: "12px" }}>Please Select Orders to Process</div>
                        </Wrapper>
                    </Allotment.Pane>
                }
            </Allotment>
        </>
    )
})

export default Step2