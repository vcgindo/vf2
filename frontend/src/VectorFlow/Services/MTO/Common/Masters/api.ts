import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace MasterService {
    export const getPlantMasterData = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getPlantMasterData/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
        })
    }

    export const getDeptMasterData = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getDeptMasterData/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
        })
    }
    export const getCCRMasterData = async () => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getCCRMasterData/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
        })
    }

}
