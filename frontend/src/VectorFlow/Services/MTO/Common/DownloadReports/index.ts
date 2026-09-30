import { useMutation, /*useQuery*/ } from '@tanstack/react-query'
import { ReportService } from './api';

export const useGetAllMTOReports = () => {
    return useMutation(async () => {
        return ReportService.getAllMTOReports();
    })
}



