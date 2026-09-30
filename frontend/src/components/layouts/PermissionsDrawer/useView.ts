import { useState, useRef } from 'react'
import { useSelector } from 'react-redux';
import { RootState } from '../../../redux/store/store';
import { notifyError, notifySuccess } from '../../../helpers/notify';
import { type GridRef } from '../../../VectorFlow/types/MDM'
import { Dispatch, SetStateAction } from 'react';
import {  useBulkUploadPermissions } from "../../../VectorFlow/Services/MTA/MDM";
import { getLocationColumns, getProductColumns } from './View';

interface UseViewProps {
    downloadFileName: string;
    setDownloadFileName: Dispatch<SetStateAction<string>>;  
    file: File | undefined;
    setFile: Dispatch<SetStateAction<File | undefined>>;   
    isUploadModalOpen: boolean;
    toggleUploadModal: (value: boolean) => void;
    onUpload: (RECORD_UPLOAD_LIMIT: any) => Promise<void>;
    setUploadCallback: (cb: () => void) => void; 
    exportToExcel: (fromUploadModal?: boolean) => Promise<void>;
    RECORD_UPLOAD_LIMIT: any;
    ref: React.MutableRefObject<GridRef | undefined>;
    showErrorRows:boolean;
    setShowErrorRows: Dispatch<SetStateAction<boolean>>;
    errorRowData: any[];   
    setErrorRowData: Dispatch<SetStateAction<any[]>>;
}

const useView = (columnDefs?: any[]): UseViewProps => {
    const [downloadFileName, setDownloadFileName] = useState('');
    const [file, setFile] = useState<File>();
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
    const ref = useRef<GridRef>();
    const EnvConfig = useSelector((state: RootState) => state.mta.EnvConfig);
    const RECORD_UPLOAD_LIMIT = EnvConfig['RECORD_UPLOAD_LIMIT'];
    const {mutateAsync : bulkUploadPermission} = useBulkUploadPermissions();
    const uploadCallbackRef = useRef<(() => void) | null>(null);

    const permissionType = columnDefs?.some(col => col.colId.includes('product')) ? 'Product' : 'Location';
    const columns = permissionType === "Product" ? getProductColumns(EnvConfig) : getLocationColumns(EnvConfig);
    const headerNameMap: Record<string, string> = {};
    const [showErrorRows,setShowErrorRows] = useState<boolean>(false);
    const [errorRowData, setErrorRowData] = useState<any[]>([]);

    columns.forEach(col => {
        headerNameMap[col.colId] = col.headerName;
    });

    const toggleUploadModal = (value: boolean) => {
        setIsUploadModalOpen(value);
    };

    const onUpload = async () => {
        try {
            if (!file) {
                notifyError('Please select a file to upload.');
                return;
            }
            const formData = new FormData();
            formData.append('file', file);  

            const headersList = columns?.filter(col => col.colId !== 'id').map(col => col.headerName);
            formData.append('headers', JSON.stringify(headersList)); 
            formData.append("permissionType", permissionType);
            
            const response = await bulkUploadPermission(formData);

            if(response?.data?.errorCount === "1")    {
                notifyError(response?.data?.msg);
                setIsUploadModalOpen(false);
                return;
            }
            if (response?.data?.data?.errorCount > 0) {
                notifyError(`Submitted ${response?.data?.data?.inserted} records out of ${response?.data?.data?.totalRows}. ${response?.data?.data?.errorCount} records have error. `)
                setShowErrorRows(true);
                setIsUploadModalOpen(false);
                const onlyRowData = (response?.data?.data?.errors || []).map((err: any) => err.rowData);
                setErrorRowData(onlyRowData);
                return;
            }
            else{
            notifySuccess(`Inserted ${response?.data?.data?.inserted} row(s) successfully`);
            toggleUploadModal(false)
            setFile(undefined);
            }

        } catch (error: any) {
            console.error(error);
            notifyError(error.message);
        } 
    };


    const exportToExcel = async (fromUploadModal?: boolean) => {
    try {
        if (fromUploadModal) {
            const downloadableColumnKeys: string[] = [];
            
            if (columnDefs) {
                columnDefs.forEach((col: any) => {
                    if (col.colId !== 'id') {
                        downloadableColumnKeys.push(col.headerName);
                    }
                });
            }

            const headers = downloadableColumnKeys.join(',');
            const csvContent = headers + '\n';
            
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = columnDefs?.some(col => col.colId.includes('product')) 
                            ? 'Product_Permissions.csv' 
                            : 'Location_Permissions.csv';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            
            notifySuccess('Template downloaded successfully');
            return;
        }
    } catch (error) {
        notifyError('Export failed');
    }
};

    return {
        downloadFileName,
        setDownloadFileName,
        file,
        setFile,
        isUploadModalOpen,
        toggleUploadModal,
        onUpload,
        setUploadCallback: (cb: () => void) => { uploadCallbackRef.current = cb; },
        exportToExcel,
        RECORD_UPLOAD_LIMIT,
        ref,
        showErrorRows,
        setShowErrorRows,
        errorRowData,
        setErrorRowData
    };
};

export default useView;