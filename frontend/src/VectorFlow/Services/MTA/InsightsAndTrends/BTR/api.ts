/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios';

export namespace BTRService{

  export const getBTRDataCount = async (body:any) => {
    return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetBTRDataCount`,body,{
      headers:{ 'Content-Type': 'application/json' }
    });
  }
    export const getBTRData = async (body:any) => {
        return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetBTRData`,body,{
          headers:{ 'Content-Type': 'application/json' }
        });
      }
}