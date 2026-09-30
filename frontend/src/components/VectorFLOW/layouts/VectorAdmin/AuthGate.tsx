import { Navigate, Outlet } from "react-router"
import { ToastContainer } from "react-toastify"
import VectorAdminLayout from "."
import { UserDataContext } from "../../../../context"
import {  useState } from "react"
import Spinner from "../../../../components/commons/Spinner"
import PageNotFound from "../../../../module-store-transfer/pages/notFound"
import { useAuth } from "./useAuth"



export const AuthGate = ()=>{


    const isLoggedIn =  localStorage.getItem('isAdmin')?true:false
    const [isSideBarOpen,toggleSidebar] = useState<boolean>(false)
    const { userData, loading, setUserData } = useAuth();
    if(!isLoggedIn){
        return <Navigate to={'/vector-admin/login'}/>
    }
    const changeColorTheme = (color: string) => {
        const newUserData: any = {...userData}
        newUserData.user.theme_ui = color
        
        setUserData(newUserData);
      }
  
    if (loading) {
        return <Spinner/>
      }
    return (
        <UserDataContext.Provider value={{ user: userData, changeColorTheme,isSideBarOpen:isSideBarOpen,toggleSideBar:toggleSidebar }}>
            <VectorAdminLayout>
                <Outlet/>
            </VectorAdminLayout>
        </UserDataContext.Provider>
    )
}


export const UnAuthGate = ()=>{

  const { isAdmin, isPermissionsManager, loading } = useAuth();

  if (loading)  return <Spinner/>

  if (isAdmin || isPermissionsManager) {
    return (
      <>
          <ToastContainer />
          <Outlet />
      </>
    );
  }
  return <PageNotFound />;
}
