import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace RMPMBufferTrendsService {
    // export const getRMPMBufferTrendsData = async () => {

    //     return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getRMPMBufferTrendData/`, {

    //         headers: {
    //             'Content-Type': 'application/json',
    //             //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
    //         }
    //     })
    // }

    export const getRMPMBufferTrendsData = async ({ appliedFilters }: any) => {
        return await axios.put(
            process.env.REACT_APP_VF_API_HOST_MTO + `/getRMPMBufferTrendData/`,
            appliedFilters, 
            {
              headers: {
                'Content-Type': 'application/json'
              }
            }
            
            
        );
    };
    

  




}
