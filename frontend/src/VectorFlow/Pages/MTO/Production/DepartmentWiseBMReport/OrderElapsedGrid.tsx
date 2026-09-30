
import React, { useEffect, useMemo, useState } from 'react';
import { useUserData } from '../../../../../context';
import {
    NoDataAvailableContainer,
    NoDataToShowDiv,
    NoDataText,
    SelectText,
    BPRViewTableWrapper,
    BPRViewTablePrefixWrapper,
    BPRViewTableHeaderTab,
    ExpansionWrapper,
    ExpansionHeader,
    ExpansionContent,
    ExpansionHeaderNormalText,
    ExpansionHeaderColoredText,
    ExpansionHeaderGroup,
    IconWrapper,
    HigHAgeingIconWrapper,
    VFWrapper
} from './styles'
import { AgGridReactProps } from 'ag-grid-react';
import { BPRViewTableGrid } from '../../../../../VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/BPR/styles';
import VFTable from '../../Common/VFTable';
//import { /*orderStatus, orderStatusData, ElapsedTime, ElapsedTimeData, */AgieingTime, ageingData } from './DeptWiseBMReportData'
import { ColorsMTO } from '../../Common/Colors';

interface orderElapsedGridProps {
    isTrue?: boolean
    data?: any
    deptName: [],
    selectedOrderCount?: string
    highAgeingdata?: any
}

type RowData = {
    [key: string]: any;
};



const OrderElapsedGrid = ({ isTrue, data, deptName, selectedOrderCount, highAgeingdata }: orderElapsedGridProps) => {

    const { user } = useUserData()
    const themeUi = user.user.theme_ui
    const [isLeftPanelOrderStatusOpen, toggleLeftPanelOrderStatus] = useState<boolean>(false);
    const [isleftPanelElapsedTimeOpen, toggleLeftPanelElapsedTime] = useState<boolean>(false)
    const [isRightPanel, toggleRightPanel] = useState<boolean>(false);
    const [leftPanelActiveTab, SetLeftPanelActiveTab] = useState<string>('Order_Status')
    const [ordeStatusColDef, setOrderStatusColdef] = useState<any>();
    const [elapsedOrderColdef, setElapsedOrderColDef] = useState<any>();
    const [highAgeingColdef, setHighAgeingColDef] = useState<any>();
    const [rowData, setRowData] = useState<any>();
    const [ElapsedTimeRowData, setElapsedTimeRowData] = useState<any>();
    const [elapsedOrderTotalDays, setElapsedOrderTotalDays] = useState<number>(0);
    const [minMaxAge, setMinMaxAge] = useState<any>({ min: '0', max: '0' })

    const sideBar = useMemo(() => {
        return {
            toolPanels: ['columns'],
        };
    }, []);

    const agGridProps: AgGridReactProps = {
        tooltipShowDelay: 0,
        tooltipTrigger: "focus",
        gridOptions: {
            rowHeight: 50,
            getRowStyle: (params: any) => {
                return {
                    background: params.node.rowIndex % 2 === 0 ? "#EBEBEB" : "#F7F7F7"
                };
            },
            pagination: true,
            defaultColDef: {
                filter: 'agTextColumnFilter',
                floatingFilter: true,
                enablePivot: true, 
                enableRowGroup: true, 
                enableValue: true, 
                sortable: true, 
                resizable: true,
                cellStyle: {
                    'text-align': 'center',
                    "font-style": "normal",
                    "font-variant": "normal",
                    //"font-weight": "300",
                    "font-size": "18px",
                    "font-family": "Roboto",
                    'text-overflow': 'ellipsis',
                    'white-space': 'nowrap',
                    'resizable': 'true',
                },
                floatingFilterComponentParams: {
                    suppressFilterButton: true
                },
                //initialFlex: 1

            },

        },
        sideBar: sideBar,
        pivotMode: false
    };

    const agGridPropsElapsedTime: AgGridReactProps = {
        tooltipShowDelay: 0,
        tooltipTrigger: "focus",
        gridOptions: {
            rowHeight: 50,
            getRowStyle: (params: any) => {
                return {
                    background: params.node.rowIndex % 2 === 0 ? "#EBEBEB" : "#F7F7F7"
                };
            },
            pagination: true, 
            suppressDragLeaveHidesColumns: true, 
            defaultColDef: {
                filter: 'agTextColumnFilter',
                floatingFilter: true,
                enablePivot: true, 
                enableRowGroup: true, 
                enableValue: true, 
                sortable: true, 
                
                resizable: true, 
                cellStyle: {
                    'text-align': 'center',
                    "font-style": "normal",
                    "font-variant": "normal",
                    "font-size": "18px",
                    "font-family": "Roboto",
                    'text-overflow': 'ellipsis',
                    'white-space': 'nowrap',
                },
                floatingFilterComponentParams: {
                    suppressFilterButton: true
                },
                initialFlex: 1
            },
            
        },
        enableRangeSelection: true,
        suppressAggFuncInHeader: true,
        suppressMakeColumnVisibleAfterUnGroup: true,
    };

    const dropDownButton = (val: number) => {
        return (
            val == 1 ?
                themeUi !== 'REGALBLAZE' ?
                    isLeftPanelOrderStatusOpen ? <IconWrapper src='/assets/img/mto/DeptWiseBmReport/arrowup.svg' /> : <IconWrapper src='/assets/img/mto/DeptWiseBmReport/arrowdown.svg' /> :
                    isLeftPanelOrderStatusOpen ? <IconWrapper src='/assets/img/mto/DeptWiseBmReport/arrowup-regal.svg' /> : <IconWrapper src='/assets/img/mto/DeptWiseBmReport/arrowdown-regal.svg' />
                :
                val == 2 ?
                    themeUi !== 'REGALBLAZE' ?
                        isleftPanelElapsedTimeOpen ? <IconWrapper src='/assets/img/mto/DeptWiseBmReport/arrowup.svg' /> : <IconWrapper src='/assets/img/mto/DeptWiseBmReport/arrowdown.svg' /> :
                        isleftPanelElapsedTimeOpen ? <IconWrapper src='/assets/img/mto/DeptWiseBmReport/arrowup-regal.svg' /> : <IconWrapper src='/assets/img/mto/DeptWiseBmReport/arrowdown-regal.svg' /> :

                    themeUi !== 'REGALBLAZE' ?
                        isRightPanel ? <IconWrapper src='/assets/img/mto/DeptWiseBmReport/arrowup.svg' /> : <IconWrapper src='/assets/img/mto/DeptWiseBmReport/arrowdown.svg' /> :
                        isRightPanel ? <IconWrapper src='/assets/img/mto/DeptWiseBmReport/arrowup-regal.svg' /> : <IconWrapper src='/assets/img/mto/DeptWiseBmReport/arrowdown-regal.svg' />

        )
    }

    /* const apiResponse: any[] = [
         {
             "cc": "ordid",
             "cp": 1,
             "hd": "Order ID",
             "v": true,
             "cla": "Centre",
             "scc": 'ord_id',
 
         },
         {
             "cc": "li",
             "cp": 2,
             "hd": "Line Item",
             "v": true,
             "cla": "Centre",
             "scc": 'li',
         },
         {
             "cc": "tq",
             "cp": 3,
             "hd": "Quantity",
             "v": true,
             "cla": "Centre",
             "scc": 'tq',
         },
         {
             "cc": "dept1",
             "cp": 4,
             "hd": "Department 1",
             "v": true,
             "cla": "Centre",
             "scc": 'dept1',
             "children": [
                 {
                     "cc": "woh",
                     "cp": 4,
                     "hd": "WIP on hand",
                     "v": true,
                     "cla": "Centre",
                     "scc": 'woh',
                 },
                 {
                     "cc": "mfg",
                     "cp": 4,
                     "hd": "Balance to manufacture",
                     "v": true,
                     "cla": "Centre",
                     "scc": 'mfg',
                 },
             ]
         },
         {
             "cc": "dept2",
             "cp": 4,
             "hd": "Department 2",
             "v": true,
             "cla": "Centre",
             "scc": 'dept2',
             "children": [
                 {
                     "cc": "woh",
                     "cp": 4,
                     "hd": "WIP on hand",
                     "v": true,
                     "cla": "Centre",
                     "scc": 'woh',
                 },
                 {
                     "cc": "mfg",
                     "cp": 4,
                     "hd": "Balance to manufacture",
                     "v": true,
                     "cla": "Centre",
                     "scc": 'mfg',
                 },
             ]
         },
         {
             "cc": "dept3",
             "cp": 4,
             "hd": "Department 3",
             "v": true,
             "cla": "Centre",
             "scc": 'dept3',
             "children": [
                 {
                     "cc": "woh",
                     "cp": 4,
                     "hd": "WIP on hand",
                     "v": true,
                     "cla": "Centre",
                     "scc": 'woh',
                 },
                 {
                     "cc": "btm",
                     "cp": 4,
                     "hd": "Balance to manufacture",
                     "v": true,
                     "cla": "Centre",
                     "scc": 'mfg',
                 },
             ]
         }
     ]*/

    const convertApiResponseToOrderStatusColDefs = (apiResponse: any[]) => {
        // Helper function to recursively map API column to ColumnDef
        const mapToColDef = (apiColumn: any) => {
            const columnDef: any = {
                headerName: apiColumn.hd,
                field: apiColumn.scc,
                colId: apiColumn.scc,
                enableRowGroup: true, // Allow grouping by this column
            enablePivot: true, // Allow pivoting on this column
            enableValue: true, // Allow aggregation on this column
            floatingFilter: true, 
            };

            if (apiColumn.children && apiColumn.children.length > 0) {
                columnDef.children = apiColumn.children.map(mapToColDef);
            }

            return columnDef;
        };

        // Map each API column entry to ColumnDef format
        return apiResponse.map(mapToColDef);
    };

    const generateApiResponse = (departmentHeaders: string[]) => {
        const apiResponse: any[] = [
            {
                cc: "ordid",
                cp: 1,
                hd: "Order ID",
                v: true,
                cla: "Centre",
                scc: 'ord_id',
            },
            {
                cc: "li",
                cp: 2,
                hd: "Line Item",
                v: true,
                cla: "Centre",
                scc: 'li',
            },
            {
                cc: "tq",
                cp: 3,
                hd: "Quantity",
                v: true,
                cla: "Centre",
                scc: 'tq',
            }
        ];

        departmentHeaders.forEach((departmentHeader, index) => {

            const departmentColumn: any = {
                cc: `dept${index + 1}`,
                cp: 4,
                hd: departmentHeader,
                v: true,
                cla: "Centre",
                scc: `dept${index + 1}`,
                children: [
                    {
                        cc: `${departmentHeader}_woh`,
                        cp: 4,
                        hd: "WIP on hand",
                        v: true,
                        cla: "Centre",
                        scc: `${departmentHeader}_woh`,
                    },
                    {
                        cc: `${departmentHeader}_mfg`,
                        cp: 4,
                        hd: "Balance to manufacture",
                        v: true,
                        cla: "Centre",
                        scc: `${departmentHeader}_mfg`,
                    }
                ]
            };

            apiResponse.push(departmentColumn);
        });

        return apiResponse;
    };

    const transformToOrderStatusRowData = () => {
        const rowData: RowData[] = [];

        // Loop through each order in the input data
        for (const [orderId, orderDetails] of Object.entries(data)) {
            if (typeof orderDetails !== 'object' || orderDetails === null) {
                continue; // Skip invalid or null entries
            }

            const orderDetailsObj = orderDetails as Record<string, unknown>;

            // Safely extract 'li' and 'tq' with type-checks
            const li = typeof orderDetailsObj.li === 'string' ? orderDetailsObj.li : '';
            const tq = typeof orderDetailsObj.tq === 'number' ? orderDetailsObj.tq : 0;

            const row: RowData = {
                ord_id: orderId,
                li,
                tq,
            };

            // Loop through each department (like "1", "2", etc.)
            for (const [deptKey, deptData] of Object.entries(orderDetailsObj)) {
                if (deptKey !== 'tq' && deptKey !== 'li' && typeof deptData === 'object' && deptData !== null) {
                    const deptInfo = deptData as {
                        woh?: number;
                        mfg?: number;
                        //int?: number | null;
                        //out?: number | null;
                    };

                    // Create fields based on department key
                    row[`${deptKey}_woh`] = deptInfo.woh ?? null;
                    row[`${deptKey}_mfg`] = deptInfo.mfg ?? null;
                    //row[`${deptKey}_int`] = deptInfo.int ?? null;
                    //row[`${deptKey}_out`] = deptInfo.out ?? null;
                }
            }

            rowData.push(row);
        }

        return rowData;
    }

    const createElapsedOrderColdef = (name: string) => {
        let colDefs = [];

        // Define column definitions based on the 'name' parameter
        switch (name) {
            case 'ET':
                colDefs = [
                    {
                        headerName: "Department",
                        field: "dept",
                        colId: "dept",
                        width: 60,
                    },
                    {
                        headerName: "In Time",
                        field: "it",
                        colId: "it",
                    },
                    {
                        headerName: "Out Time",
                        field: "ot",
                        colId: "ot",
                    },
                    {
                        headerName: "Elapsed Time",
                        field: "et",
                        colId: "et",
                        cellStyle: {
                            color: ColorsMTO.Pink.code,
                        },
                    },
                ];
                break;

            case 'HA':
                colDefs = [
                    {
                        headerName: "Order ID",
                        field: "oid",
                        colId: "oid",
                    },
                    {
                        headerName: "Line Item",
                        field: "lid",
                        colId: "lid",
                    },
                    {
                        headerName: "Batch No.",
                        field: "bn",
                        colId: "bn",
                    },
                    {
                        headerName: "Department",
                        field: "dept",
                        colId: "dept",
                    },
                    {
                        headerName: "Ageing",
                        field: "age",
                        colId: "age",
                        cellStyle: {
                            color: ColorsMTO.Pink.code,
                        },
                    },

                ];
                break;

            // Add more cases as needed for different 'name' values

            default:
                colDefs = [
                    {
                        headerName: "Default Column",
                        field: "default",
                        colId: "default",
                    },
                ];
                break;
        }

        return colDefs;
    };

    // Function to format date and time in "1 Feb 2024, 10:00am" format
    const formatDateTime = (dateTime: string): string => {
        const date = new Date(dateTime);

        if (isNaN(date.getTime())) {
            return "Invalid date"; // Handle invalid date case
        }

        // Options for formatting the date and time
        const dateOptions: Intl.DateTimeFormatOptions = {
            day: "numeric",
            month: "short",
            year: "numeric"
        };

        /*  const timeOptions: Intl.DateTimeFormatOptions = {
              hour: "numeric",
              minute: "numeric",
              hour12: true // To display in 12-hour format with am/pm
          };*/

        const formattedDate = date.toLocaleDateString("en-GB", dateOptions);
        //const formattedTime = date.toLocaleTimeString("en-GB", timeOptions);

        return `${formattedDate}`;
        //${formattedTime}`
    };

    const transformToElapsedTimeRowData = () => {
        // Filter out keys that are not department-related (e.g., 'tq', 'li')
        const dynamicKeys = Object.keys(data).filter(key => key !== 'tq' && key !== 'li');
        // Build row data using the dynamic keys
        const rowData: RowData[] = dynamicKeys.flatMap(deptKey => {
            const deptData = data[deptKey];
            // Handle the case where deptData contains an object with nested keys
            const nestedKeys = Object.keys(deptData);
            return nestedKeys.flatMap(nestedDeptKey => {
                const nestedDeptData = deptData[nestedDeptKey];

                // Ensure we find 'int' and 'out' within the nested object
                const nestedInTime = nestedDeptData?.int;
                const nestedOutTime = nestedDeptData?.out;

                if (nestedInTime && nestedOutTime) {
                    return [{
                        dept: nestedDeptKey,  // Use the nested key as the dept value
                        it: formatDateTime(nestedInTime),
                        ot: formatDateTime(nestedOutTime),
                        et: calculateElapsedTime(nestedInTime, nestedOutTime),  // Calculate elapsed time
                    }];
                }
                return [];
            });
            return [];
        });

        return rowData;
    }

    // Function to calculate the time difference between "out" and "int" (in days or any desired unit)
    const calculateElapsedTime = (inTime: string, outTime: string): string => {
        const inDate = new Date(inTime);
        const outDate = new Date(outTime);
        if (isNaN(inDate.getTime()) || isNaN(outDate.getTime())) {
            return "Invalid date"; // Handle invalid date case
        }

        // Calculate the difference in milliseconds
        const timeDifference = outDate.getTime() - inDate.getTime();

        // Calculate the difference in days and hours
        const totalHours = timeDifference / (1000 * 3600); // Total hours
        const days = Math.floor(totalHours / 24); // Whole days
        //const hours = Math.floor(totalHours % 24); // Remaining hours

        // Construct the string with days and hours
        return `${days} days`;
        /* ${hours} hrs*/
    };

    // Function to parse elapsed time string to total days
    const parseElapsedTime = (elapsedTime: string): number => {
        // Handle the case where elapsedTime is negative
        const match = elapsedTime.match(/(-?\d+) days/);
        return match ? parseFloat(match[1]) : 0;
    };

    // Function to keep the row data with the highest elapsed time for each department
    const filterMaxElapsedTimePerDept = (rowData: RowData[]): RowData[] => {
        const deptMap = new Map<string, RowData>();

        rowData.forEach(row => {
            const currentElapsedTimeInDays = parseElapsedTime(row.et);

            // If department is not in the map or current row has a higher elapsed time
            // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
            if (!deptMap.has(row.dept) || parseElapsedTime(deptMap.get(row.dept)!.et) < currentElapsedTimeInDays) {
                deptMap.set(row.dept, row);
            }
        });

        // Return the values (rows) of the map
        return Array.from(deptMap.values());
    };

    // Function to calculate the total days from the elapsed time column
    const calculateTotalElapsedDays = (rowData: RowData[]): number => {
        //console.log('rowData', rowData)
        return rowData.reduce((total, row) => total + parseElapsedTime(row.et), 0);
    };


    useEffect(() => {
        if (data) {
            /**This will create the UI Configuration api response */
            const apiResponse = generateApiResponse(deptName);

            /**Based on the apiResponse creating th dynamic coldef */
            const columnDefs = convertApiResponseToOrderStatusColDefs(apiResponse);
            //console.log('coldef', columnDefs)
            setOrderStatusColdef(columnDefs)

            const elapsedOrderColdef = createElapsedOrderColdef('ET');
            //console.log('elapsedOrderColdef', elapsedOrderColdef)
            setElapsedOrderColDef(elapsedOrderColdef)

            const highAgeingColDef = createElapsedOrderColdef('HA');
            //console.log('highAgeingColDef',highAgeingColDef)
            setHighAgeingColDef(highAgeingColDef)

            //this will create the row data
            const rowData = transformToOrderStatusRowData();//const rowData = generateRowData(columnDefs);
            setRowData(rowData)
            //console.log('rowData=Fristan', rowData);


            const ElapsedTimeAllRowData = transformToElapsedTimeRowData();
            // console.log('ElapsedTimeRowData', ElapsedTimeAllRowData)
            const ElapsedTimeRowData = filterMaxElapsedTimePerDept(ElapsedTimeAllRowData)
            //console.log('findtotal', ElapsedTimeAllRowData)
            const totalDays = calculateTotalElapsedDays(ElapsedTimeRowData)
            setElapsedOrderTotalDays(totalDays)
            //console.log('totalDays',totalDays)
            setElapsedTimeRowData(ElapsedTimeRowData)

            const { minAge, maxAge } = findAgeRange();
            setMinMaxAge({ min: minAge, max: maxAge })

        }
    }, [data])

    const findAgeRange = (): { minAge: number, maxAge: number } => {
        // if (highAgeingdata?.length === 0) {
        //     throw new Error("The array of people is empty.");
        // }

        // Initialize minAge and maxAge with the age of the first person
        let minAge = highAgeingdata[0]?.age;
        let maxAge = highAgeingdata[0]?.age;

        // Iterate through the array to find the min and max age
        for (const person of highAgeingdata) {
            if (person.age < minAge) {
                minAge = person.age;
            }
            if (person.age > maxAge) {
                maxAge = person.age;
            }
        }

        return { minAge, maxAge };
    };



    return (
        isTrue ?
            <div style={{ display: 'flex', gap: "2rem", marginBottom: "2rem" }}>
                <BPRViewTableWrapper>
                    <BPRViewTablePrefixWrapper>
                        <BPRViewTableHeaderTab
                            themeUi={themeUi}
                            zIndex={leftPanelActiveTab === 'Order_Status' ? 1 : 0}
                            marLeft={false}
                            status={leftPanelActiveTab === 'Order_Status' ? "active" : 'inactive'}
                            onClick={() => SetLeftPanelActiveTab('Order_Status')}
                        >
                            Order Status
                        </BPRViewTableHeaderTab>
                        <BPRViewTableHeaderTab
                            themeUi={themeUi}
                            zIndex={leftPanelActiveTab === 'Elapsed_Time' ? 1 : 0}
                            marLeft={false}
                            status={leftPanelActiveTab === 'Elapsed_Time' ? "active" : 'inactive'}
                            onClick={() => SetLeftPanelActiveTab('Elapsed_Time')}
                        >
                            Elapsed Time
                        </BPRViewTableHeaderTab>
                    </BPRViewTablePrefixWrapper>

                    <BPRViewTableGrid style={{ padding: '10px', borderRadius: 0 }}>
                        {leftPanelActiveTab === 'Order_Status' ?
                            <ExpansionWrapper>
                                <ExpansionHeader style={{ borderBottom: isLeftPanelOrderStatusOpen ? 'solid 1px #E3ACC9' : 'none' }}>
                                    <ExpansionHeaderGroup>
                                        <ExpansionHeaderNormalText>
                                            Selected Orders  :
                                        </ExpansionHeaderNormalText>
                                        <ExpansionHeaderColoredText>
                                            {selectedOrderCount}
                                        </ExpansionHeaderColoredText>
                                    </ExpansionHeaderGroup>
                                    <ExpansionHeaderGroup style={{ marginLeft: '10px' }}>
                                        <ExpansionHeaderNormalText>
                                            WIP Present In  :
                                        </ExpansionHeaderNormalText>
                                        <ExpansionHeaderColoredText>
                                            {`${deptName}${deptName.length > 1 ? ',' : ''}`}
                                        </ExpansionHeaderColoredText>
                                    </ExpansionHeaderGroup>
                                    <ExpansionHeaderGroup onClick={() => toggleLeftPanelOrderStatus(!isLeftPanelOrderStatusOpen)} style={{ marginLeft: 'auto' }}>
                                        {
                                            dropDownButton(1)
                                        }
                                    </ExpansionHeaderGroup>
                                </ExpansionHeader>
                                {(isLeftPanelOrderStatusOpen) && (
                                    <ExpansionContent>
                                        <VFWrapper style={{height: "400px"}}>
                                            <VFTable
                                                {...agGridProps}
                                                columnDefs={ordeStatusColDef}
                                                rowData={rowData}
                                                height='400px'
                                            />
                                        </VFWrapper>
                                    </ExpansionContent>
                                )}
                            </ExpansionWrapper>
                            :
                            <ExpansionWrapper>
                                <ExpansionHeader style={{ borderBottom: isleftPanelElapsedTimeOpen ? 'solid 1px #E3ACC9' : 'none' }}>
                                    <ExpansionHeaderGroup>
                                        <ExpansionHeaderNormalText>
                                            Selected Orders  :
                                        </ExpansionHeaderNormalText>
                                        <ExpansionHeaderColoredText>
                                            {selectedOrderCount}
                                        </ExpansionHeaderColoredText>
                                    </ExpansionHeaderGroup>
                                    <ExpansionHeaderGroup style={{ marginLeft: '10px' }}>
                                        <ExpansionHeaderNormalText>
                                            Elapsed Time  :
                                        </ExpansionHeaderNormalText>
                                        <ExpansionHeaderColoredText>
                                            {elapsedOrderTotalDays + ' Days'}
                                        </ExpansionHeaderColoredText>
                                    </ExpansionHeaderGroup>
                                    <ExpansionHeaderGroup onClick={() => toggleLeftPanelElapsedTime(!isleftPanelElapsedTimeOpen)} style={{ marginLeft: 'auto' }}>
                                        {
                                            dropDownButton(2)
                                        }
                                    </ExpansionHeaderGroup>
                                </ExpansionHeader>
                                {(isleftPanelElapsedTimeOpen) && (
                                    <ExpansionContent >
                                        <VFWrapper style={{height: "400px"}}>
                                            <VFTable
                                                {...agGridPropsElapsedTime}
                                                height='400px'
                                                rowData={ElapsedTimeRowData}
                                                columnDefs={elapsedOrderColdef}
                                                />
                                        </VFWrapper>
                                    </ExpansionContent>
                                )}
                            </ExpansionWrapper>
                        }
                    </BPRViewTableGrid>
                </BPRViewTableWrapper>

                <BPRViewTableWrapper >
                    <BPRViewTablePrefixWrapper>
                        <BPRViewTableHeaderTab
                            bgColor='red'
                            themeUi={themeUi}
                            zIndex={1}
                            marLeft={false}
                            status="active"
                        >
                            <HigHAgeingIconWrapper
                                src='/assets/img/mto/DeptWiseBmReport/highageing.svg'
                            />
                            High Ageing Batches
                        </BPRViewTableHeaderTab>
                    </BPRViewTablePrefixWrapper>

                    <BPRViewTableGrid style={{ padding: '10px', borderRadius: 0 }}>
                        <ExpansionWrapper>
                            <ExpansionHeader style={{ borderBottom: isRightPanel ? 'solid 1px #E3ACC9' : 'none' }}>
                                <ExpansionHeaderGroup>
                                    <ExpansionHeaderNormalText>
                                        No. Of batches  :
                                    </ExpansionHeaderNormalText>
                                    <ExpansionHeaderColoredText>
                                        {highAgeingdata?.length}
                                    </ExpansionHeaderColoredText>
                                </ExpansionHeaderGroup>
                                <ExpansionHeaderGroup style={{ marginLeft: 'auto' }}>
                                    <ExpansionHeaderNormalText>
                                        Min Ageing  :
                                    </ExpansionHeaderNormalText>
                                    <ExpansionHeaderColoredText>
                                        {minMaxAge.min}
                                    </ExpansionHeaderColoredText>
                                </ExpansionHeaderGroup>
                                <ExpansionHeaderGroup style={{ marginLeft: 'auto' }}>
                                    <ExpansionHeaderNormalText>
                                        Max Ageing  :
                                    </ExpansionHeaderNormalText>
                                    <ExpansionHeaderColoredText>
                                        {minMaxAge.max}
                                    </ExpansionHeaderColoredText>
                                </ExpansionHeaderGroup>
                                <ExpansionHeaderGroup onClick={() => toggleRightPanel(!isRightPanel)} style={{ marginLeft: '100px' }}>
                                    {
                                        dropDownButton(3)
                                    }
                                </ExpansionHeaderGroup>
                            </ExpansionHeader>
                            {(isRightPanel) && (
                                <ExpansionContent>
                                    <VFWrapper style={{height: "400px"}}>
                                        <VFTable
                                            {...agGridProps}
                                            height='400px'
                                            columnDefs={highAgeingColdef}
                                            rowData={highAgeingdata}
                                        />
                                    </VFWrapper>
                                </ExpansionContent>
                            )}
                        </ExpansionWrapper>
                    </BPRViewTableGrid>
                </BPRViewTableWrapper>
            </div>

            :

            <NoDataAvailableContainer style={{marginBottom: "2rem"}}>
                <NoDataToShowDiv>
                    <NoDataText>No Data To Show</NoDataText>
                    <SelectText>Please select a row from above table to view data</SelectText>
                </NoDataToShowDiv>
            </NoDataAvailableContainer>
    )
}

export default OrderElapsedGrid