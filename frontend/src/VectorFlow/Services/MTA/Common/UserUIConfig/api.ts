import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace UserUIConfigService {

    export const getState = async (payload: any) => {
        return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/GetState`, payload, {
            headers: { 'Content-Type': 'application/json' }
        });
    }

    export const saveState = async (payload: { reportname: string, state: string }) => {
        return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/SaveState`, payload, {
            headers: { 'Content-Type': 'application/json' }
        });
    }

    export const resetState = async (payload: any) => {
        return await axios.post(process.env.REACT_APP_API_HOST + `api/mta/ResetState`, payload, {
            headers: { 'Content-Type': 'application/json' }
        });
    }
    
}
