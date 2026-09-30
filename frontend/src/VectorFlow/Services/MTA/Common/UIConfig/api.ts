import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace UIConfigService {

    export const getUIConfigData = async (reportName: string) => {

        return await axios.get(process.env.REACT_APP_API_HOST + `api/mta/GetUIConfig?reportName=${reportName}`, {
            headers: { 'Content-Type': 'application/json' }
        })

    }
    
}
