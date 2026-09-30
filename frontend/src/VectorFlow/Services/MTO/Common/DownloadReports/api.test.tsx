
import { ReportService } from './api';
import axios, { AxiosStatic } from 'axios';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<AxiosStatic>;

describe('UIConvfig Service', () => {
    const OLD_ENV = process.env;
    beforeEach(() => {
        jest.resetModules() // Most important - it clears the cache
        process.env = { ...OLD_ENV }; // Make a copy
    });
    process.env.REACT_APP_VF_API_HOST_MTO = 'http://10.8.1.10:9000/api/mto'

    afterEach(() => {
        jest.clearAllMocks();
    });


    it('should fetch all reports', async () => {
        mockedAxios.get.mockResolvedValueOnce({ data: {
            "VflowService": {
                "path": "C:\\Users\\VflowAdmin2\\Downloads\\BuffersToBeAdded.zip",
                "downloadName": "VflowService.zip",
                "reportName": "VFlow File Example",
                "fileType": "application/zip"
            },
            "NMSAddNewSKULoc": {
                "path": "F:\\\\Download Reports\\\\UIUploadLogs\\NMSAddNewSKULocLog.zip",
                "downloadName": "NMSAddNewSKULocLog.zip",
                "reportName": "UI Upload Logs - Add New SKU-Loc",
                "fileType": "application/zip"
            },
            "NMSModifySKULoc": {
                "path": "F:\\\\Download Reports\\\\UIUploadLogs\\NMSModifySKULocLog.zip",
                "downloadName": "NMSModifySKULocLog.zip",
                "reportName": "UI Upload Logs - Modify SKU-Loc",
                "fileType": "application/zip"
            },
            "NMSRemoveSKULoc": {
                "path": "F:\\\\Download Reports\\\\UIUploadLogs\\NMSRemoveSKULocLog.zip",
                "downloadName": "NMSRemoveSKULocLog.zip",
                "reportName": "UI Upload Logs - Remove SKU-Loc",
                "fileType": "application/zip"
            },
            "NMSSKUMaster": {
                "path": "F:\\\\Download Reports\\\\UIUploadLogs\\NMSSKUMasterLog.zip",
                "downloadName": "NMSSKUMasterLog.zip",
                "reportName": "UI Upload Logs - SKU Master",
                "fileType": "application/zip"
            },
            "NMSLocMaster": {
                "path": "F:\\\\Download Reports\\\\UIUploadLogs\\NMSLocMasterLog.zip",
                "downloadName": "NMSLocMasterLog.zip",
                "reportName": "UI Upload Logs - Location Master",
                "fileType": "application/zip"
            },
            "NMSMOQMaster": {
                "path": "F:\\\\Download Reports\\\\UIUploadLogs\\NMSMOQMasterLog.zip",
                "downloadName": "NMSMOQMasterLog.zip",
                "reportName": "UI Upload Logs - MOQ Master",
                "fileType": "application/zip"
            },
            "NMSSOBMaster": {
                "path": "F:\\\\Download Reports\\\\UIUploadLogs\\NMSSOBMasterLog.zip",
                "downloadName": "NMSSOBMasterLog.zip",
                "reportName": "UI Upload Logs - SOB Master",
                "fileType": "application/zip"
            },
            "ForceNormChangeUpload": {
                "path": "F:\\\\Download Reports\\\\UIUploadLogs\\ForceNormChangeUploadLog.zip",
                "downloadName": "ForceNormChangeUploadLog.zip",
                "reportName": "UI Upload Logs - Force Norm Change",
                "fileType": "application/zip"
            },
            "InputData": {
                "path": "F:\\\\Download Reports\\InputData.zip",
                "downloadName": "InputData.zip",
                "reportName": "Input Data",
                "fileType": "application/zip"
            }
        }, status: 200 });
        const response = await ReportService.getAllMTOReports()
        expect(response.status).toBe(200); 
    }); 
});