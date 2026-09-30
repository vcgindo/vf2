import { useMutation } from '@tanstack/react-query'
import { OrderAtRiskService } from './api';

export const useGetOrderRiskData = () => {
    return useMutation(async(params: any) => {
        return await OrderAtRiskService.getOrderAtRiskData(params);
    });
}

export const useGetOrderRiskDataExcelExport = () => {
    return useMutation(async(params: any) => {
        return await OrderAtRiskService.getOrderAtRiskDataExcelExport(params);
    });
}
