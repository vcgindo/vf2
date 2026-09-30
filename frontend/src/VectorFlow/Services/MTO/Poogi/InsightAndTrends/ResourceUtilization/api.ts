import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace ResourceUtilizationService {


    export const getResourceUtilizationData = async (startDate: string, endDate: string, ccrName?: string, plantName?: string, deptName?: string) => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getResourceUtilizationAndWIPProfileData/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
            params: {
                hs: startDate,
                he: endDate,
                ccrid: ccrName,
                plantid: plantName,
                deptid: deptName
            }
        })
    }


}
