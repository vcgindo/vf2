import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace UIConfigService {

    export const getUIConfigData = async (reportName: string) => {

            return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getUIReportConfiguration/?reportName=${reportName}&group=${(reportName === 'BMReport' || reportName === 'DeptWiseReport') ? 1 : 0}`,
                {
            headers: {
                'Content-Type': 'application/json',
            }
        })
    }

}

export type getUIAndUserConfigDataPayload ={
    reportName:string;
    userName?:string;
    reportNameId?:number;
}

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace UIConfigService {
    export const getUIAndUserConfigData = async (
      payload: getUIAndUserConfigDataPayload
    ) => {
      return await axios.get(
        `${process.env.REACT_APP_VF_API_HOST_MTO}/getUpdatedUserwiseUIReportConfigurationData/`,
        {
          params: {
            group:
            ['BMReport', 'DeptWiseReport'].includes(payload.reportName)
                ? 1
                : 0,
            ...payload,
          },
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
    };
  }
  
