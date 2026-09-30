/* eslint-disable @typescript-eslint/no-namespace */
import axios from "axios";

import {RRRDataPayload} from '../../../../types/RRR'

export namespace SDRServices {

    export const getSDRUIConfiguration = async () => {
        return await axios.get(process.env.REACT_APP_API_HOST+ `api/mta/SDRUIConfig`);
      }
    
    export const getSDRData = async (body:RRRDataPayload) => {
      return await axios.post(process.env.REACT_APP_API_HOST+ `api/mta/GetSupplierDispatchReportData`,body,{
        headers:{ 'Content-Type': 'application/json' }
      });
    }

    export const getSDRDataCount = async (body:RRRDataPayload) => {
      return await axios.post(process.env.REACT_APP_API_HOST+ `api/mta/GetSupplierDispatchReportDataCount`,body,{
        headers:{ 'Content-Type': 'application/json' }
      });
    }
}