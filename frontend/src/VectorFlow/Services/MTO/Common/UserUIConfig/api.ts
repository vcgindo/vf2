import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace UserUIConfigService {

    export const getUserUIReportConfigData = async ({un, rn_id}: {un: string, rn_id: number}) => {
    
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getUserwiseUIReportConfigurationData/?userName=${un}&reportNameId=${rn_id}`, {
            headers: {
                'Content-Type': 'application/json',
            }
        })
    }
    
    export const updateUserUIReportConfigData = async (payload: {un: string, rn_id: number, cs: string}) => {
    
        return await axios.put(process.env.REACT_APP_VF_API_HOST_MTO + `/UpdateUserwiseUIReportConfigurationData/`, 
        payload,
        {
            headers: {
                'Content-Type': 'application/json',
            }
        })
    }

}
