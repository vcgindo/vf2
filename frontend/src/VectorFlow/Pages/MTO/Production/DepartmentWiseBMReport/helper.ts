import _ from "lodash";

export enum BMReportAnaytics {
  INCREASE = "increase",
  DECREASE = "decrease",
  INCREASE_DECREASE = "increase_decrease",
  DECREASE_INCREASE = "decrease_increase",
  EQUAL = "equal",
}

const calcValue = (tc: number, yc: number, tcp: number, ycp: number) => {
  //When Both Count and Percent are Equal
  if (tc == yc && tcp == ycp) {
    return BMReportAnaytics.EQUAL;
  }
  //When Both Count and Percent Increase
  if (tc > yc && tcp > ycp) {
    return BMReportAnaytics.INCREASE;
  }
  //When Both Count and Percent Decrease
  if (tc < yc && tcp < ycp) {
    return BMReportAnaytics.DECREASE;
  }
  //When Count Increases and Percent Decreases
  if (tc > yc && tcp < ycp) {
    return BMReportAnaytics.INCREASE_DECREASE;
  }
  //When Count Decreases and Percent Increases
  if (tc < yc && tcp > ycp) {
    return BMReportAnaytics.DECREASE_INCREASE;
  }
};

export const modifyAnalyticsData = (response: any) => {
  const newResponse = _.transform(
    response,
    function (result: any, val: any, key: any) {
      result[key.toLowerCase()] = val;
    }
  );
  const analytics: any = [];
  const colors = Object.keys(newResponse?.prod || {});

  colors.forEach((color) => {
    if (newResponse.proc[color]) {
      const {
        tc: procTc,
        tcp: procTcp,
        yc: procYc,
        ycp: procYcp,
      } = newResponse.proc[color];
      const {
        tc: prodTc,
        tcp: prodTcp,
        yc: prodYc,
        ycp: prodYcp,
      } = newResponse.prod[color];
      analytics.push({
        color: color.toLowerCase(),
        ProcCount: procTc,
        ProcPer: procTcp,
        ProdCount: prodTc,
        ProdPer: prodTcp,
        ProcValue: calcValue(procTc, procTcp, procYc, procYcp),
        ProdValue: calcValue(prodTc, prodTcp, prodYc, prodYcp),
      });
    }
  });

  return analytics;
};
