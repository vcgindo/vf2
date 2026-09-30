import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace TrendsFailureReasonsService {

    export const getTrendsFailureData = async ({appliedFilters}: any) => {
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getTrendOfFailureReasonsData/`, 
        appliedFilters,
        {
            headers: {
                'Content-Type': 'application/json',
            }
        })
    }

}
