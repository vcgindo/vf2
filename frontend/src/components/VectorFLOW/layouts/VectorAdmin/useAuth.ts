import { useState, useEffect } from 'react';
import { MainService } from '../../../../module-main/services/api';// Adjust this import path as needed
import { notifyError } from "../../../../helpers/notify"// Adjust this import path as needed


export const useAuth = () => {
    const [userData, setUserData] =  useState<any>({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        

        MainService.getProfile()
            .then((res) => {
                setUserData(res.data.data);
            })
            .catch((err) => {
                console.error("Your session has expired",err)
                notifyError("Your session has expired. Please log in again.");
                localStorage.removeItem('isAdmin');
                localStorage.clear()
            })
            .finally(() => {

                setLoading(false);
            });
    }, []); 

    const isAdmin = !!userData?.user?.is_admin;
    const isPermissionsManager  = userData?.roles?.permission.includes("PermissionsManager");
    return {  userData, isAdmin, loading, setUserData , isPermissionsManager };
};