import { useEffect, useRef, useState } from "react";
// import { AgChartOptions } from "ag-charts-community";
import { AgCharts } from "ag-charts-react";
import MTOActionToolBar from "../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar";
// import { APIMock } from "./mockData";
import { DayPicker } from "react-day-picker";
import CustomCalenderCaption from "./CustomCalenderCaption";
import CustomCalenderDay from "./CustomCalenderDay";
import { useUserData } from "../../../../../../context/index";
import VFCapsule from "../../../../../../components/VectorFLOW/commons/VFCapsule";
import {
  CalenderHeading,
  CalenderLabel,
  CalenderWrapper,
  CapsuleWrapper,
  ChartHeaderRadioGroup,
  ColoredMarker,
  GraphWrapper,
  HorizontalLineDashed,
  HorizontalWrapper,
  MarkerWrapper,
  RadioGroup,
  SCChartSliderContainer,
  SCVerticalDividerGray,
  SectionFlex,
  SelectGroup,
  VerticalTitle,
  VerticalWrapper,
} from "./styles";
import { useGetResourceUtilizationData } from "../../../../../../VectorFlow/Services/MTO/Poogi/InsightAndTrends/ResourceUtilization";
import { useGetDate } from "../../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/RMPMExpediting";
import moment from "moment";
import { useGetCCRMasterData, useGetDeptMasterData, useGetPlantMasterData } from "../../../../../../VectorFlow/Services/MTO/Common/Masters";
import VFRangeSlider from "../../../Common/VFRangeSlider";
import OverlayLoader from "../../../Common/Loader";
import { toast } from "react-toastify";
import { notifyError, notifySuccess } from "../../../../../../helpers/notify";
import VFSelect from "../../../../../../components/VectorFLOW/commons/MTO/VFSelect";
import { useDispatch } from "react-redux";
import { RESOURCE_UTIL_ANALYTICS } from "../../../../../../redux/actions/MTO";
import VFButton from "../../../../../../components/VectorFLOW/commons/VFButton";
import { Rectangle } from "../../../Common/Rectangle/RectangleMarker";

const SearchIcon = () => {
  return (
      <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 20 20.002" data-testid='vfmaster-search-icon'>
          <g id="Group_3376" data-name="Group 3376" transform="translate(-905.1 -140.058)">
              <g id="b995a33f0790c855384b59de531e8fe3" transform="translate(905.1 140.058)">
                  <path id="Path_90" data-name="Path 90" d="M16.352,24.4A8.152,8.152,0,1,1,24.5,16.252,8.163,8.163,0,0,1,16.352,24.4Zm0-15.093a6.982,6.982,0,1,0,6.982,6.982A6.994,6.994,0,0,0,16.352,9.312Z" transform="translate(-8.2 -8.1)" fill="#313131" />
                  <path id="Path_91" data-name="Path 91" d="M45.786,46.664,40.1,41.02l.92-.92,5.644,5.686-.878.878" transform="translate(-26.664 -26.662)" fill="#313131" />
              </g>
          </g>
      </svg>
  )
}


const ResourceUtilization = () => {
  const chartRef = useRef<any>(null);
  const [horizonDays, setHorizonDays] = useState(90);
  const [selectedGraphState, setSelectedGraphState] = useState("wipLimit");
  const [actBtn, setActBtn] = useState({
    label: "Over Limit",
    value: "Over Limit",
  });
  const { user } = useUserData();
  const themeUi = user.user.theme_ui;
  const { mutateAsync: getResourceUtilizationData, isLoading, isSuccess, isError } = useGetResourceUtilizationData();
  const { mutateAsync: getPlantMaster } = useGetPlantMasterData();
  const { mutateAsync: getDeptMaster } = useGetDeptMasterData();
  const { mutateAsync: getCCRMaster } = useGetCCRMasterData();
  const { data: apiResponseData, /*isLoading, refetch*/ } = useGetDate();
  const date = apiResponseData?.data?.data;
  const [selectedCCR, setSelectedCCR] = useState<any>(undefined);
  const [defaultCCR, setDefaultCCR] = useState<any>();
  const [selectedPlant, setSelectedPlant] = useState<any>({ label: 'Select Plant', value: '' });
  const [selectedDept, setSelectedDept] = useState<any>({ label: 'Select Department', value: '' });
  const [apiData, setApiData] = useState<any>(null);
  const [plantOpts, setPlantOpts] = useState([]);
  const [deptOpts, setDeptOpts] = useState([]);
  const [ccrOpts, setCCROpts] = useState([]);
  const [masterCCROptions, setMaterCCROptions] = useState([]);
  const [masterDept, setMasterDept] = useState([]);
  const [horizonClicked, setHorizonClicked] = useState(false);

  const [utilData, setUtilData] = useState<any>();
  const [wipOverData, setWipOverData] = useState<any>();
  const [wipUnderData, setWipUnderData] = useState<any>();
  const defaultDepartment = { label: 'Select Department', value: '' };
  const dispatch = useDispatch()

  const GetData = async () => {
    try {

      const apiBody = {
        startDate: moment(date).subtract(horizonDays, 'days').format().substring(0, 10),
        endDate: moment(date).format().substring(0, 10),
        ccrName: selectedCCR?.value,
        plantName: selectedPlant.value,
        deptName: selectedDept.value
      }

      const response = await getResourceUtilizationData(apiBody);
      setApiData(response.data.data)
    }
    catch (error) {
      console.log(error)
    }
  }

  const GetMasterData = async () => {
    try {
      const responsePlant = await getPlantMaster();
      const plants = responsePlant.data.data;
      const myPlantOpts: any = [];
      plants.forEach((e: any) => {
        myPlantOpts.push({ value: e.plant_id, label: e.plant_name })
      })

      setPlantOpts(myPlantOpts);
      const responseDept = await getDeptMaster();
      const depts = responseDept.data.data;
      const myDeptOpts: any = [];
      depts.forEach((e: any) => {
        myDeptOpts.push({ value: e.dept_id, label: e.dept_name })
      })
      setMasterDept(depts)
      setDeptOpts(myDeptOpts);
    }
    catch (error) {
      console.log(error);
    }
  }

  const checkOptions = (CCRarr: any, ccrName: string) => {

    for (let i = 0; i < CCRarr?.length; i++) {
      if (CCRarr[i].label === ccrName) {
        return true;
      }
    }
    return false;
  }

  const getCCROptions = async (apiData: any) => {
    try {
      const responseCCR = await getCCRMaster();
      const ccrs = responseCCR.data.data;
      const myCCROpts: any = [];
      const newMasterCCROpts: any = [];
      const oLimit = apiData?.wiplimit?.olimit?.map((l: any) => l.ccr) || [];
      const uLimit = apiData?.wiplimit?.ulimit?.map((l: any) => l.ccr) || [];
      const apiOptions = [...oLimit, ...uLimit];
      ccrs.forEach((e: any) => {
        newMasterCCROpts.push(e)
        if (apiOptions.includes(e.ccr_name) && !checkOptions(myCCROpts, e.ccr_name)) {
          myCCROpts.push({ value: e.ccr_id, label: e.ccr_name })
        }
      })
      setMaterCCROptions(newMasterCCROpts)
      setCCROpts(myCCROpts);
    } catch (error) {
      console.log(error);
    }
  }


  const createAnalyticsData = (apiData: any) => {
    if (selectedGraphState === 'wipLimit') {
      const newAnalyticsData = {
        type: 'wip',
        ol: apiData.wiplimit.olimit.length,
        ul: apiData.wiplimit.ulimit.length,
      }

      dispatch(RESOURCE_UTIL_ANALYTICS(newAnalyticsData));

    }
    else {
      let six = 0;
      let sixeight = 0;
      let eight = 0;

      apiData.utilization.forEach((ele: any) => {
        if (ele.aup < 60) {
          six++;
        }
        else if (ele.aup >= 60 && ele.aup <= 80) {
          sixeight++;
        }
        else {
          eight++;
        }
      })
      const newAnalyticsData = {
        type: 'util',
        sixty: six,
        sixeight,
        eight
      }
      dispatch(RESOURCE_UTIL_ANALYTICS(newAnalyticsData));


    }
  }

  const filterDepartment = () => {
    const depts = masterDept;
    const myDeptOpts: any = [];
    const deptIds: any[] = [];
    for (let i = 0; i < masterCCROptions?.length; i++) {
      const ccr: any = masterCCROptions[i];
      if (selectedPlant.value === ccr?.plant && !deptIds.includes(ccr.dept)) {
        deptIds.push(ccr?.dept);
      }
    }
    depts.forEach((e: any) => {
      if (deptIds?.includes(e.dept_id)) {
        myDeptOpts.push({ value: e.dept_id, label: e.dept_name })
      }
    })
    setDeptOpts(myDeptOpts);
  }

  useEffect(() => {
    if (apiData) {
      getCCROptions(apiData)
    }

  }, [apiData])

  useEffect(() => {
    if (apiData) {
      createAnalyticsData(apiData);
    }
  }, [selectedGraphState])

  useEffect(() => {
    if (selectedPlant?.value) {
      filterDepartment()
    }
  }, [selectedPlant, masterDept])

  useEffect(() => {
    GetData();
    GetMasterData();
  }, [])

  useEffect(() => {
    setActBtn({
      label: "Over Limit",
      value: "Over Limit",
    })
    GetData();
    // GetMasterData();
  }, [selectedCCR, horizonClicked])

  useEffect(() => {
    if (isSuccess) {
      toast.dismiss()
      notifySuccess("Fetched data successfully!")
    }
    if (isError) {
      toast.dismiss()
      notifyError("Failed to fetch data!")
    }
  }, [isSuccess, isError])

  useEffect(() => {
    const newUtilData: any = [];
    const newWipOverData: any = [];
    const newWipUnderData: any = [];
    if (apiData && apiData.utilization) {

      apiData.utilization.sort((a: any, b: any) => {
        return b.aup - a.aup;
      })

      apiData.utilization.forEach((e: any) => {
        newUtilData.push({ ccr: e.ccr, limit: e.aup })
      })
    }
    if (apiData && apiData.wiplimit) {

      apiData.wiplimit.olimit.sort((a: any, b: any) => {
        return b.us - a.us;
      });

      apiData.wiplimit.olimit.forEach((e: any) => {
        newWipOverData.push({ overLimit: Number(e.awip), limit: e.lm, ccr: e.ccr, us: e.us })
      })

      apiData.wiplimit.ulimit.sort((a: any, b: any) => {
        return b.us - a.us; // Ascending order, use b.awip - a.awip for descending
      });
      apiData.wiplimit.ulimit.forEach((e: any) => {
        newWipUnderData.push({ underLimit: e.awip, limit: e.lm, ccr: e.ccr, us: e.us })

      })
    }

    setUtilData(newUtilData);
    setWipOverData(newWipOverData);
    setWipUnderData(newWipUnderData);

    if (apiData && apiData.ccr && apiData.ccr.ccr_id && !selectedCCR) {

      setDefaultCCR({ value: apiData?.ccr.ccr_id, label: apiData?.ccr.ccr_name })
    }
    else {
      setDefaultCCR(selectedCCR)
    }

  }, [apiData])

  useEffect(() => {
    setUtilizationOptions({ ...utilizationOptions, data: utilData })
  }, [utilData])

  useEffect(() => {
    setWipOptions({ ...wipOptions, data: wipOverData })
  }, [wipOverData, wipUnderData])

  function TooltipRenderer({ datum }: any) {
    return `
      <div class="ag-chart-tooltip-title" style="background-color: #2E2E2E; display: flex; justify-content: flex-start; align-items: center; min-width: 200px">
          Details
      </div>
      <div class="ag-chart-tooltip-content" style="color: white; background-color: #2E2E2E; padding: 0px 20px;">
      <div style="border-top: 1px dashed lightgray"></div>
      <div style="width: 100%; padding: 10px 5px;">
          <div style="display: flex; width: 100%;">
              
          ${selectedGraphState === "wipLimit"
        ? `<div style="display: flex; flex-direction: column ;flexwidth: 100%;">
          <div style="display: flex; align-items: center">
              <div style="margin-right: 10px;  margin-top: 5px; height: 4px; width: 10px; background-color: #de6057"></div>
              <div style="display:flex; justify-content: space-between; width: 100%;">
                  <div style="padding-right: 80px">Limit</div>
                  <span>${actBtn?.label === "Over Limit" ? datum?.limit : datum?.limit}</span>
              </div>
            </div>
          <div style="display: flex">
              <div style="margin-right: 10px;  margin-top: 5px; height: 10px; width: 10px; background-color: #000000"></div>
              <div style="display:flex; justify-content: space-between; width: 100%;">
                  <div>Usage (days)</div>
                  <div>${actBtn?.label === "Over Limit" ? datum?.overLimit : datum?.underLimit}</div>
              </div>
            </div>
          <div style="display: flex">
              <div style="margin-right: 10px;  margin-top: 5px; height: 10px; width: 10px; background-color: #000000"></div>
              <div style="display:flex; justify-content: space-between; width: 100%;">
                  <div>Usage %</div>
                  <div>${actBtn?.label === "Over Limit" ? datum?.us : datum?.us}</div>
              </div>
            </div>
          
           
          </div>`
        : ""
      }
      </div>`;
  }

  const getUtilizationColor = (date: any) => {

    const redDates: any = [];
    const yellowDates: any = [];

    if (apiData && apiData?.analytics) {

      const dates = Object.keys(apiData.analytics)

      dates.forEach((e: any) => {
        if (apiData.analytics[e].up > 85) {
          let currDate = e;
          currDate = currDate.split('-')[2] + '-' + currDate.split('-')[1] + '-' + currDate.split('-')[0];
          redDates.push(currDate);
        }
        else if (apiData.analytics[e].up < 60) {
          // underLimit.push(moment(e).calendar().replaceAll('/', '-'));
        }
        else {
          let currDate = e;
          currDate = currDate.split('-')[2] + '-' + currDate.split('-')[1] + '-' + currDate.split('-')[0];
          yellowDates.push(currDate);

        }
      })
    }

    const day = date.getDate().toString().padStart(2, "0");
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    const year = date.getFullYear();
    const newDate = `${day}-${month}-${year}`;

    if (redDates.includes(newDate)) {
      return "Red";
    }
    if (yellowDates.includes(newDate)) {
      return "Yellow";
    }
    return "default";
  };


  const getWIPColor = (date: any) => {
    const overLimit: any = [];
    const underLimit: any = [];

    if (apiData && apiData?.analytics) {

      const dates = Object.keys(apiData.analytics)

      dates.forEach((e: any) => {
        if (apiData.analytics[e].wc === 'ol') {
          let currDate = e
          currDate = currDate.split('-')[2] + '-' + currDate.split('-')[1] + '-' + currDate.split('-')[0];
          overLimit.push(currDate);
        }
        else if (apiData.analytics[e].wc === 'ul') {
          let currDate = e;
          currDate = currDate.split('-')[2] + '-' + currDate.split('-')[1] + '-' + currDate.split('-')[0];
          underLimit.push(currDate);
        }
      })

    }

    const day = date.getDate().toString().padStart(2, "0");
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    const year = date.getFullYear();
    const newDate = `${day}-${month}-${year}`;

    if (overLimit.includes(newDate)) {
      return "Red";
    }
    if (underLimit.includes(newDate)) {
      return "Green";
    }
    return "default";
  };

  const handlePlantChange = (option: any) => {
    setSelectedPlant(option);
    setSelectedDept(defaultDepartment);
  };
  const handleDeptChange = (option: any) => setSelectedDept(option);


  const [utilizationOptions, setUtilizationOptions] = useState<any>({
    data: utilData,
    series: [
      {
        type: "bar",
        xKey: "ccr",
        yKey: "limit",
        yName: "Utilization",
        stacked: true,
        fill: "#A8A8A8",
        highlightStyle: {
          item: {
            fill: "#B93B7E",
            stroke: "#B93B7E",
            strokeWidth: 2,
          },
        },
        tooltip: {
          renderer: (datum: any) => {
            return `
      <div class="ag-chart-tooltip-title" style="background-color: #2E2E2E; display: flex; justify-content: flex-start; align-items: center; min-width: 200px">
          Details
      </div>
      <div class="ag-chart-tooltip-content" style="color: white; background-color: #2E2E2E; padding: 0px 20px;">
      <div style="border-top: 1px dashed lightgray"></div>
      <div style="width: 100%; padding: 10px 5px;">
          <div style="display: flex; width: 100%;">
              
         
                 <div style="display: flex; width: 100%;">
              <div style="margin-right: 10px; display: flex; flex-direction: column; margin-top: 5px; height: 10px; width: 10px; background-color: #000000"></div>
              <div style="display:flex; justify-content: space-between; width: 100%;">
                  <div>Usage</div>
                  <div>${datum.datum?.limit} %</div>
              </div>
          </div>
      </div>`;
          }
        },
      },
    ],

    axes: [
      {
        type: "category",
        position: "bottom",
        title: {
          text: "",
          fontSize: 10,
          fontWeight: "bold",
        },
        label: {
          fontSize: 8,
          fontWeight: "bold",
          color: "black",
          padding: 10,
        },
        gridLine: {
          enabled: false,
        },
      },
      {
        title: {
          text: "",
          fontSize: 10,
          fontWeight: "bold",
          spacing: 3,
        },
        type: "number",
        position: "left",
        line: { enabled: true },
        label: {
          fontSize: 8,
          fontWeight: "bold",
          color: "black",
          formatter(params: any) {
            return params?.value + "%";
          },
        },
        gridLine: {
          enabled: false,
        },
      },
    ],
    background: {
      fill: "transparent", // Set the background to transparent
    },
    legend: {
      position: "bottom",
      item: {
        showSeriesStroke: true,
        marker: {
          size: 15,
          strokeWidth: 0,
          shape: "square",
        },
      },
    },
  })

  const [wipOptions, setWipOptions] = useState<any>({
    data: wipOverData,

    series: [
      {
        type: "bar",
        xKey: "ccr",
        yKey: "overLimit",
        yName: "Released",
        stacked: true,
        fill: "#000000",
        highlightStyle: {
          item: {
            fill: "#D2CECE",
            stroke: "#D2CECE",
            strokeWidth: 2,
          },
        },
        tooltip: {
          renderer: TooltipRenderer,
        },
      },
      {
        type: "scatter",
        xKey: "ccr",
        yKey: (actBtn.label === 'Over Limit') ? "limit" : 'none',
        yName: "Limit",
        marker: {
          size: 10,
          fill: "#E96666",
          shape: Rectangle,
          strokeWidth: 0,
        },
        highlightStyle: {
          item: {
            fill: "#820F4C",
            stroke: "#820F4C",
            strokeWidth: 2,
          },
        },
        tooltip: {
          renderer: TooltipRenderer,
        },
      },
    ],

    axes: [
      {
        type: "category",
        position: "bottom",
        title: {
          text: "",
          fontSize: 10,
          fontWeight: "bold",
        },
        label: {
          fontSize: 8,
          fontWeight: "bold",
          color: "black",
          padding: 0,

        },

        gridLine: {
          enabled: false,
        },
      },
      {
        title: {
          text: "WIP In Days",
          fontSize: 10,
          fontWeight: "bold",
          spacing: 3,
        },
        type: "number",
        position: "left",
        line: { enabled: true },
        label: {
          fontSize: 8,
          fontWeight: "bold",
          color: "black",
        },
        gridLine: {
          enabled: false,
        },
      },
    ],
    background: {
      fill: "transparent",
    },
    legend: {
      position: "bottom",
      item: {
        showSeriesStroke: true,
        // paddingY: 0,
        marker: {
          size: 15,
          strokeWidth: 0,
          shape: "square",
        },
      },

    },
    padding: {
      bottom: 0,
    },
  })

  useEffect(() => {

    if (actBtn.label === 'Over Limit') {

      setWipOptions({
        ...wipOptions,
        data: wipOverData,

        series: [{
          type: "bar",
          xKey: "ccr",
          yKey: "overLimit",
          yName: "Released",
          stacked: true,
          fill: "#000000",
          highlightStyle: {
            item: {
              fill: "#D2CECE",
              stroke: "#D2CECE",
              strokeWidth: 2,
            },
          },
          tooltip: {
            renderer: TooltipRenderer,
          },
        },
        {
          type: "scatter",
          xKey: "ccr",
          yKey: "limit",
          yName: "Limit",
          marker: {
            size: 10,
            fill: "#E96666",
            shape: Rectangle,
            strokeWidth: 0,
          },
          highlightStyle: {
            item: {
              fill: "#820F4C",
              stroke: "#820F4C",
              strokeWidth: 2,
            },
          },
          tooltip: {
            renderer: TooltipRenderer,
          },
        }]
      })
    }
    else {
      setWipOptions({
        ...wipOptions,
        data: wipUnderData,
        series: [{
          type: "bar",
          xKey: "ccr",
          yKey: "underLimit",
          yName: "Released",
          stacked: true,
          fill: "#000000",
          highlightStyle: {
            item: {
              fill: "#D2CECE",
              stroke: "#D2CECE",
              strokeWidth: 2,
            },
          },
          tooltip: {
            renderer: TooltipRenderer,
          },
        },
        {
          type: "scatter",
          xKey: "ccr",
          yKey: "limit",
          yName: "Limit",
          marker: {
            size: 10,
            fill: "#E96666",
            shape: Rectangle,
            strokeWidth: 0,
          },
          highlightStyle: {
            item: {
              fill: "#820F4C",
              stroke: "#820F4C",
              strokeWidth: 2,
            },
          },
          tooltip: {
            renderer: TooltipRenderer,
          },
        }]
      })
    }

  }, [actBtn, horizonClicked])

  const handleHorizonSubmit = () => {
    setHorizonClicked(!horizonClicked)

  };

  const updateGraphState = (id: number, option: string) => {
    setSelectedGraphState(option);
  };

  const handleLimitGraphChange = () => {
    if (actBtn.label === "Over Limit") {
      setActBtn({
        label: "Under Limit",
        value: "Under Limit",
      });
    } else {
      setActBtn({
        label: "Over Limit",
        value: "Over Limit",
      });
    }
  };


  const WIPFilter: any =
    (
      <div data-testid='resourceUtilization' style={{ display: ' flex', alignItems: 'flex-start', gap: '20px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div style={{
            fontStyle: "normal",
            fontVariant: "normal",
            fontWeight: 300,
            fontSize: 14,
            fontFamily: "Roboto",
            width: 'max-content'
          }}
          >
            Please choose an option:
          </div>
          <RadioGroup>
            <ChartHeaderRadioGroup style={{ gap: '4px' }} theme={themeUi}>
              <input type="radio" checked={selectedGraphState === 'wipLimit'} value="wipLimit" name="wipLimit" id="wipLimit" data-testid="wip-limit-radio" onChange={() => updateGraphState && updateGraphState(1, 'wipLimit')} style={{ margin: 0, zoom: 1.8, cursor: 'pointer' }} />
              <label htmlFor="parent" style={{ fontSize: '14px', fontWeight: 500 }}>WIP Limit</label>
            </ChartHeaderRadioGroup>
            <ChartHeaderRadioGroup style={{ marginLeft: '10px', gap: '4px' }} theme={themeUi}>
              <input type="radio" checked={selectedGraphState === 'utilization'} value="utilization" name="utilization" id="utilization" data-testid="utilization-radio" onChange={() => updateGraphState && updateGraphState(2, 'utilization')} style={{ margin: 0, zoom: 1.8, cursor: 'pointer' }} />
              <label htmlFor="child" style={{ fontSize: '14px', fontWeight: 500 }}>Utilization</label>
            </ChartHeaderRadioGroup>
          </RadioGroup>
        </div>
        <div style={{ marginTop: '30px' }}>
          <SCVerticalDividerGray />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div
            style={{
              fontStyle: "normal",
              fontVariant: "normal",
              fontWeight: 300,
              fontSize: 14,
              fontFamily: "Roboto",
            }}
            data-testid="select-plnt"
          >
            Select Plant
          </div>
          <SelectGroup style={{ width: '130px', zoom: '1.25' }}>
            <VFSelect
              themeUi={themeUi}
              placeholder={"Plant"}
              options={plantOpts}
              isSelected={selectedPlant.value}
              onChange={handlePlantChange}
              icon={SearchIcon}
            />
            {/* <CustomSelect placeholder="Select Plant" value={selectedPlant} onSelectionChanged={(e: any) => { console.log("selected this", e) }} selected={false} options={plantOpts} optionsWidth={"100%"} /> */}
          </SelectGroup>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div
            style={{
              fontStyle: "normal",
              fontVariant: "normal",
              fontWeight: 300,
              fontSize: 14,
              fontFamily: "Roboto",
            }}
            data-testid="select-dept"
          >
            Select Department
          </div>
          <SelectGroup style={{ width: '160px', zoom: '1.25' }}>
            <VFSelect
              themeUi={themeUi}
              placeholder={"Department"}
              isSelected={selectedDept.value}
              options={deptOpts}
              onChange={handleDeptChange}
              icon={SearchIcon}
            />
          </SelectGroup>
        </div>
        <div style={{ marginTop: '30px' }}>
          <SCVerticalDividerGray />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{
            fontStyle: "normal",
            fontVariant: "normal",
            fontWeight: 300,
            fontSize: 14,
            fontFamily: "Roboto",
          }}
          >
            Select Horizon(in Days):
          </div>
          <SCChartSliderContainer>
            <VFRangeSlider
              showTriangle={false}
              min={1}
              max={90}
              milestones={[0, 30, 60, 90]}
              strictMode={false}
              width={250}
              defaultValue={horizonDays || 0}
              handleChange={(e) => { setHorizonDays && setHorizonDays(e) }}
              labelValueFormatter={(value: number) => value > 1 ? `${value}` : `${value}`}
            />
            <div>
              {/* <VFButtonOutline themeUi={user.user.theme_ui} onClick={handleSubmitClick} width={120} disabled={false} style={{fontSize:'15px',height:'42px',fontWeight:500}}>
                                    Submit
                                </VFButtonOutline> */}
              {/* <img
                data-testid='horizon-submit'
                style={{ cursor: 'pointer' }}
                src={themeUi === "REGALBLAZE" ? "/assets/img/Group 627-regal.svg" : "/assets/img/Group 627.svg"}
                height={50}
                width={60}
                onClick={() => handleHorizonSubmit && handleHorizonSubmit()}
              /> */}
              <VFButton
              onClick={() => handleHorizonSubmit && handleHorizonSubmit()}
              themeUi={themeUi}
              disabled={false}
              style={{
                height: "40px",
                width: "50px",
                borderRadius: "3px",
              }}
            >
              <img
                src="/assets/img/rightArrowHorizontal.svg"
                height={13}
                width={7}
              />
            </VFButton>
            </div>
          </SCChartSliderContainer>
        </div>
      </div>)



  return (
    <div>
      {isLoading && <OverlayLoader />}
      <MTOActionToolBar
        themeUi={themeUi}
        comp={"resourceUtilization"}
        WIPFilter={WIPFilter}
      />
      <HorizontalWrapper>
        <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
          {
            selectedGraphState === "wipLimit" && (


              <CapsuleWrapper
                style={{
                  zoom: 1,
                  padding: "4px",
                  // position: "absolute",
                  marginRight: "2rem",
                  right: "10px",
                  top: "10px",
                  zIndex: 8,
                }}
              >
                <VFCapsule
                  activeBtn={actBtn}
                  capsules={[
                    {
                      label: "Under Limit",
                      value: "Under Limit",
                    },
                    {
                      label: "Over Limit",
                      value: "Over Limit",
                    },
                  ]}
                  handleClick={() => handleLimitGraphChange()}
                />
              </CapsuleWrapper>
            )

          }
          <GraphWrapper>
            <div style={{ width: "90%", height: "100" }}>
              <AgCharts
                ref={chartRef}
                options={
                  (selectedGraphState === "wipLimit")
                    ? wipOptions
                    : utilizationOptions
                }
              />
            </div>
          </GraphWrapper>

        </div>
        <VerticalWrapper>
          <SectionFlex>
            <VerticalTitle>Analytics</VerticalTitle>
            <div data-testid="custom-select" style={{ width: "100%" }}>
              <VFSelect
                themeUi={themeUi}
                placeholder={'Select CCR'}
                value={defaultCCR ? defaultCCR : selectedCCR}
                options={ccrOpts}
                onChange={(e: any) => { setSelectedCCR(e), setDefaultCCR(e) }}
              />
            </div>
          </SectionFlex>
          <HorizontalLineDashed />
          <div style={{ display: "flex", flexDirection: 'column', zoom: 0.8 }}>

            <div style={{ padding: "10px", width: '100%' }}>
              <CalenderLabel>
                <MarkerWrapper>
                  <ColoredMarker color={"#A2A2A2"} />
                  &lt;60%
                </MarkerWrapper>
                <MarkerWrapper>
                  <ColoredMarker color="#EBBF2C" />
                  60-85%
                </MarkerWrapper>
                <MarkerWrapper>
                  <ColoredMarker color="#E53F3F" />
                  85%+
                </MarkerWrapper>
              </CalenderLabel>
              <CalenderWrapper>
                <CalenderHeading data-testid="utilization">Utilization</CalenderHeading>
                <DayPicker
                  style={{

                    display: 'flex',
                    justifyContent: 'center'
                  }}
                  mode="single"
                  components={{
                    Caption: CustomCalenderCaption,
                    Day: (props) => {
                      return (
                        <CustomCalenderDay
                          {...props}
                          color={getUtilizationColor(props.date)}
                        />
                      );
                    },
                  }}
                  styles={{
                    cell: {
                      padding: "5px",
                    },
                  }}
                />
              </CalenderWrapper>
            </div>
            <HorizontalLineDashed />
            <div style={{ padding: "10px", width: '100%' }}>
              <CalenderLabel>
                <MarkerWrapper>
                  <ColoredMarker color="#33800B" />
                  Under Limit
                </MarkerWrapper>
                <MarkerWrapper>
                  <ColoredMarker color="#E53F3F" />
                  Over Limit
                </MarkerWrapper>

              </CalenderLabel>
              <CalenderWrapper>
                <CalenderHeading data-testid="wipControl">WIP Control</CalenderHeading>
                <DayPicker
                  style={{
                    // zoom: 0.8,
                    display: 'flex',
                    justifyContent: 'center'
                  }}
                  mode="single"
                  components={{
                    Caption: CustomCalenderCaption,
                    Day: (props) => {
                      return (
                        <CustomCalenderDay
                          {...props}
                          color={getWIPColor(props.date)}
                        />
                      );
                    },
                  }}
                  styles={{
                    cell: {
                      padding: "5px",
                    },
                  }}
                />
              </CalenderWrapper>
            </div>
          </div>
        </VerticalWrapper>
      </HorizontalWrapper>
    </div>
  );
};

export default ResourceUtilization;
