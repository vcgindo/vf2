import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace FilterDataService {
    
    export const getFilterData = async (params?: any) => {
        const response = await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getfilterData/`, {
            headers: {
                'Content-Type': 'application/json',
            },
            params
        });
        return response;
    }
}
