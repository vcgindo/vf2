import { AgChartOptions } from "ag-charts-community";
import "allotment/dist/style.css";
import { useEffect, useMemo, useState } from "react";
import VFCapsule from "../../../../../../../components/VectorFLOW/commons/VFCapsule";
import VFInfoToolTip from "../../../../../../../components/VectorFLOW/commons/VFInfoToolTip";
import { getColumnDefinations } from "../../../../../../../helpers/utils";
import SplitGraphContainer from "../../../../../../../VectorFlow/Pages/MTO/Common/SplitGraphContainer";
import { ProductionInsightsAndTrendsString } from "../../../../Common/String";
import { createSeriesData, TooltipRenderer } from "../OrderBalanceCommon";
import { columnConfigData } from "../OrderBalanceMockData";
import { CapsuleWrapper } from "../styles";
// <-------------- uncomment below code to enable dropdown for orderType    --------->
import VFSelect from "../../../../../../../components/VectorFLOW/commons/MTO/VFSelect";
import { useUserData } from "../../../../../../../context/index";




const TrailDeptBalance = (props: any) => {
  const {
    graphData,
    // <-------------- uncomment below code to enable dropdown for orderType    --------->
    orderOptions,
    handleChange,
    lastRunDate
    //orderType
  } = props;
  const [hideChart1, toggleChart1] = useState(false);
  const [chartLoading, setChartLoading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [rawData, setRawData] = useState([]);
  const [actBtn, setActBtn] = useState({
    label: "Bal To Mfg.",
    value: "Bal To Mfg.",
  });
  const { user } = useUserData();
  const themeUi = user.user.theme_ui;
  const options: AgChartOptions = {
    data: rawData,
    series: createSeriesData(),
    axes: [
      {
        type: "category",
        position: "bottom",
        title: {
          text: "Trailing Department",
          fontSize: 10,
          fontWeight: "bold",
        },
        label: {
          fontSize: 8,
          fontWeight: "bold",
          color: "black",
        },
        gridLine: {
          enabled: false,
        },
      },
      {
        title: {
          text: "Quantity (in UOM)",
          fontSize: 10,
          fontWeight: "bold",
          spacing: 3,
        },
        type: "number",
        line: { enabled: true },
        position: "left",
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

    legend: {
      item: {
        label: {
          fontSize: 10,
        },
      },
    },
  };

  const colDefs = useMemo(() => {
    return getColumnDefinations(columnConfigData?.tableColumn, {}, []);
  }, []);

  const updateGraphState = (capsule: any) => {
    setActBtn(capsule);
  };

  // <-------------- uncomment below code to enable dropdown for orderType    --------->

  /*const customStyles = {
    control: (provided: any) => ({
      ...provided,
      width: 180,
    }),
    menu: (provided: any) => ({
      ...provided,
      width: 180,
    }),
    placeholder: (provided: any) => ({
      ...provided,
      color: 'gray', // Customize the placeholder color
      fontSize: '15px', // Customize the font size
    }),
    option: (provided: any, state: any) => ({
      ...provided,
      backgroundColor: state.isSelected ? 'lightblue' : 'white',
      color: 'black',
      '&:hover': {
        backgroundColor: 'lightgray',
      },
    }),
    dropdownIndicator: (provided: any) => ({
      ...provided,
      color: "grey",
      padding: "5px",
      margin: '5px'
    }),
  };*/

  const   SearchIcon = () => {
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

  const generateHeader = () => {
    // <-------------- uncomment below code to enable dropdown for orderType    --------->
    const options = orderOptions?.map((opt: any) => ({ label: opt.desc, value: opt.order_type }))

    return (
      <div
        className="title"
        style={{
          backgroundColor: "white",
          height: "40px",
          display: "flex",
          // <-------------- uncomment below code to enable dropdown for orderType    --------->
          justifyContent: "space-between",
          //justifyContent: "end",
          alignItems: "center",
          width: "100%",
        }}
      >
        {/* <-------------- uncomment below code to enable dropdown for orderType    ---------> */}
        <div style={{ display: 'flex', alignItems: 'center', marginLeft: '30px' }}>
          <p style={{ fontFamily: 'roboto', fontSize: '15px', fontWeight: '500', paddingRight: '5px', zoom: 0.75 }}>Order Type</p>
          <div >
            <VFSelect
              themeUi={themeUi}
              placeholder={"Select Order Type"}
              options={options}
              onChange={handleChange}
              icon={SearchIcon}
            />
            {/* <Select
              isSearchable={true}
              components={{
                IndicatorSeparator: () => null,
                DropdownIndicator: SearchIcon
              }}
              styles={{
                container: (base) => ({
                  ...base,
                  //width: "100%"
                  width: 170
                }),
                control: (base: any, state: any) => ({
                  ...base,
                  minHeight: "25px",
                  minWidth: "80px",
                  boxShadow: state.isFocused ? 0 : 0,
                  border: "1px solid hsl(0, 0%, 80%) !important",
                  '&:hover': {
                    border: "1px solid hsl(0, 0%, 80%)"
                  }
                }),
                menu: (base) => ({
                  ...base,
                  zIndex: "100000000",
                  minWidth: "100%",
                  width: "max-content"
                }),
                menuList: (base) => ({
                  ...base,
                  maxHeight: "120px"
                }),
                dropdownIndicator: (base) => ({
                  ...base,
                  color: "grey",
                  padding: "0"
                }),
                clearIndicator: (base) => ({
                  ...base,
                  color: "grey",
                  padding: "0"
                }),
                indicatorsContainer: (base) => ({
                  ...base,
                  padding: "0 8px"
                })
              }}
              placeholder="Select Order Type"
              options={options}
              onChange={handleChange}
            /> */}
          </div>

        </div>
        <div style={{ display: "flex", alignItems: "center" }}>
          <CapsuleWrapper style={{ zoom: 1, padding: "4px" }}>
            <VFCapsule
              activeBtn={actBtn}
              capsules={[
                {
                  label: "Bal To Mfg.",
                  value: "Bal To Mfg.",
                },
                {
                  label: "Bal To Disp.",
                  value: "Bal To Disp.",
                },
              ]}
              handleClick={updateGraphState}
            />
          </CapsuleWrapper>
          <div style={{ marginLeft: 30, marginBottom: "-5px" }}>
            <VFInfoToolTip
              infoList={[
                `The graph highlights trailing department wise quantities balance to ${actBtn.label === "Bal To Mfg." ? "manufacture" : "dispatch"
                }`,
              ]}
            />
          </div>
          <div
            data-testid="grid-toggle-btn"
            onClick={() => {
              toggleChart1(!hideChart1);
            }}
            style={{
              marginLeft: 10,
              marginBottom: "-5px",
              marginRight: "10px",
            }}
          >
            <img
              src="/assets/img/VectorFLOW/BPR/minimize.svg"
              height={13}
              width={13}
              color={"#CCCCCC"}
            />
          </div>
        </div>
      </div>
    );
  };

  const tableTitle =
    actBtn.label === "Bal To Mfg."
      ? ProductionInsightsAndTrendsString.trailDeptMfg
      : ProductionInsightsAndTrendsString.trailDeptDisp;

  useEffect(() => {
    if (graphData?.mfg) {
      const response: any = graphData?.mfg;
      const data: any = Object.keys(response)?.map((key: string) => ({
        trailDept: key,
        b: response[key]?.Black || 0,
        r: response[key]?.Red || 0,
        y: response[key]?.Yellow || 0,
        g: response[key]?.Green || 0,
        bl: response[key]?.Blue || 0,
        w: response[key]?.White || 0,
      }));
      setRawData(data);
    }
  }, [graphData])

  useEffect(() => {

    let response: any = {};
    if (actBtn.label === "Bal To Mfg.") {
      response = graphData?.mfg || {};
    } else {
      response = graphData?.disp || {};
    }

    const data: any = Object.keys(response)?.map((key: string) => ({
      trailDept: key,
      b: response[key]?.Black || 0,
      r: response[key]?.Red || 0,
      y: response[key]?.Yellow || 0,
      g: response[key]?.Green || 0,
      bl: response[key]?.Blue || 0,
      w: response[key]?.White || 0,
    }));

    setRawData(data);

  }, [actBtn])

  const graphTitleJSX = <div
    data-testid="ot-if-graph"
    style={{
      fontSize: "13px",
      margin: "0 auto",

      textAlign: "center",
    }}
  >
    <span style={{ fontWeight: 500 }}>{`${actBtn.label === "Bal To Mfg."
      ? ProductionInsightsAndTrendsString.trailDeptMfg
      : ProductionInsightsAndTrendsString.trailDeptDisp}  `}</span>
    <span style={{ fontWeight: 300 }}>{`(${lastRunDate})`}</span>
  </div>


  return (
    <div
      data-testid="mfg-disp-graph"
      style={{ height: "100%", display: "flex", justifyContent: "left", marginLeft: '12px', paddingBottom: '10px' }}
    >

      <SplitGraphContainer
        tableLoading={tableLoading}
        chartLoading={chartLoading}
        setTableLoading={setTableLoading}
        setChartLoading={setChartLoading}
        data={rawData}
        rowData={options.data}
        graphTitle={``}
        graphTitleJSX={graphTitleJSX}
        tableTitle={tableTitle}
        options={options}
        colDef={colDefs}
        header={generateHeader}
        hideChart={hideChart1}
        toggleChart={toggleChart1}
        TooltipRenderer={TooltipRenderer}
        graphType={7}
      />
    </div>
  );
};

export default TrailDeptBalance;
