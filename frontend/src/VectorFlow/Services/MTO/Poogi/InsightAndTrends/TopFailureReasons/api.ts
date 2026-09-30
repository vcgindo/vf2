import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace TopFailureReasonsService {

    export const getTopFailureData = async ({graphflag, page, appliedFilters,page_size}: any) => {
        if(graphflag){
            return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getTopFailureReasonsData/`, {
                headers: {
                    'Content-Type': 'application/json',
                },
                params: {
                    graphflag,
                }
            })
        }
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getTopFailureReasonsData/`, 
        appliedFilters,
        {
            headers: {
                'Content-Type': 'application/json',
            },
            params: {
                graphflag,
                page,
                page_size
            }
        })
    }

}
