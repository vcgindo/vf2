/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios';

export namespace EnquiryResponseService {

    export const getEnquiryData = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getEnquiryResponseData/`, {
            headers: { 'Content-Type': 'application/json' },
            
        });
    }
}