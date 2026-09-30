
import axios from 'axios';
// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace RMPMExpedtingServices {

    export const getLastRunDate = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getRunDate/`, {
            headers: {
                'Content-Type': 'application/json',
            }
        })
    }

    export const getRMPMExpedition = async (data: any) => {
        if (data.val === 'all') {
            return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getExpiditingRMData/?rm_horizon=${data.horizon}&supplier_horizon=${data.horizon}`, 
            data.appliedFilters,
            {
                headers: {
                    'Content-Type': 'application/json',
                }
            })
        }
        else if (data.val === 'rm') {
            return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getExpiditingRMData/?rm_horizon=${data.horizon}`, 
            data.appliedFilters,
            {
                headers: {
                    'Content-Type': 'application/json',
                }
            })
        }
        else {
            return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/getExpiditingRMData/?supplier_horizon=${data.horizon}`, 
            data.appliedFilters,
            {
                headers: {
                    'Content-Type': 'application/json',
                }
            })
        }

    }
}