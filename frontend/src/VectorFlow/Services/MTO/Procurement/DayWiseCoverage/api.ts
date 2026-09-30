import axios from "axios"

    export const getDayWiseCoverageData = async (startDate: string, endDate: string, plannedReleaseDate: string | undefined) => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getDayWiseCoverageData/`, {
            headers: {
                'Content-Type': 'application/json',
                //'X-CSRFToken': 'RYW30tp0vOYHuintw34PVIwgqdUrLADeO0ADgpwgYz8KFDCxbSY7Bt6PAalrUUp2'
            },
            params:{
                FromDate: startDate,
                ToDate: endDate,
                planned_release_date: plannedReleaseDate,
            }
        })
    }

