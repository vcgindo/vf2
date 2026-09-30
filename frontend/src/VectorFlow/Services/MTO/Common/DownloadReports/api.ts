import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace ReportService {

    export const getAllMTOReports = async () => {

        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/GetAllReportData/`, {
            headers: {
                'Content-Type': 'application/json',
            }
        })
    }

}
