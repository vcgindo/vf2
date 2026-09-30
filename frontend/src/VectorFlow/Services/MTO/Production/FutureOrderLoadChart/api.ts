import axios from 'axios';

export interface FutureOrderLoadChartPayload {
    // graphFlag: number;
    isExcelExport?:boolean
    loadwise: number;
    view: string;
    filters: {
      ccr?: string;
      orderOption?: string;
      from: string;
        to: string;
        horizon_date?: any;
    };
    report_name?: string;
    graphflag?: number;
  }

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace FutureOrderLoadChartServices {

    export const getFutureOrderFOLHorizonDate = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getFutureOrderLoadCCRFOLHorizonDate/`, {
            headers: {
                'Content-Type': 'application/json',
            }
        })
    }

    export const getFutureOrderLoadChartData = async ( body: FutureOrderLoadChartPayload) => {
        return await axios.post(process.env.REACT_APP_VF_API_HOST_MTO + `/getFutureOrderLoadChartData/`, body, {
            headers: {
                'Content-Type': 'application/json',
            }
        })
    }

    //excle ka
    export const getFutureOrderLoadChartExcelData = async ({ body,payload, isExcelExport, report_name, graphflag }: any) => {
        return await axios.post(
            process.env.REACT_APP_VF_API_HOST_MTO + `/getFutureOrderLoadChartData/?export=${isExcelExport}&report_name=${report_name}&graphflag=${graphflag}`,
            {...body, ...payload},
            {
                headers: {
                    'Content-Type': 'application/json',
                },
                responseType: "blob"
            }
        )
    }



}


