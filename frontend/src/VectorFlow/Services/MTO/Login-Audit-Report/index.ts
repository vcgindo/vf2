import { useMutation } from "@tanstack/react-query"; // Import useMutation
import { getLoginAuditReportData } from "./api";

export const useLoginAuditReport = () => {
return useMutation(async () => {
        return getLoginAuditReportData();
    })
}