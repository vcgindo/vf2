import React, { type PropsWithChildren, useEffect, useRef, useState } from 'react'
import {getRedirecting, loginRedirect } from '../../../helpers/utils'
import { MainService } from '../../../module-main/services/api'
import { useLocation, useNavigate } from 'react-router'
import { useUserData } from '../../../context';
import { listMenuParent } from "../NavbarMenu/listMenu";

interface AuthenticationTemplateProps {
  isAnonymous: boolean
  loadingComponent: React.ReactElement,
  setMenuItem:any;
}

export const AuthenticationTemplate = ({
  isAnonymous,
  loadingComponent,
  children,
  setMenuItem
}: PropsWithChildren<AuthenticationTemplateProps>) => {
  if (isAnonymous) {
    return <UnauthenticatedTemplate>{children}</UnauthenticatedTemplate>
  } else {
    return (
      <AuthenticatedTemplate loadingComponent={loadingComponent} setMenuItem={setMenuItem}>
        {children}
      </AuthenticatedTemplate>
    )
  }
}

const getSelectedMenuItem = (permission: string) => {

  function findParentMenuByUrl(
    menuList: any[],
    targetUrl: string,
    parent: any = null
  ): any | null {

    for (let i = 0; i < menuList.length; i++) {
      const menu = menuList[i];

      // If at top level, set itself as parent
      const currentParent = parent ?? menu;

      // Match found
      if (menu.url === targetUrl) {
        return currentParent;
      }

      // Search in children
      if (menu?.child?.length) {
        const found = findParentMenuByUrl(menu.child, targetUrl, currentParent);
        if (found) return found;
      }
    }

    return null; 
  }

  return findParentMenuByUrl(listMenuParent, permission);
};


const AuthenticatedTemplate = (
  props: PropsWithChildren<
  Pick<AuthenticationTemplateProps, 'loadingComponent' | 'setMenuItem'>
  >
) => {

  const {user, setUser}  = useUserData();
  const { children, loadingComponent: Loading } = props;
  const [loading,setLoading] = useState(false);

  const navigate = useNavigate();
  const location = useLocation()
   
    useEffect(() => {
      const verifyUserSession = async () => {
        try {
          if (getRedirecting()) return;

          const response = await MainService.getProfile();
          const profile = response?.data?.data;

          if (profile) {
            setUser(profile);

            const selectedMenu = getSelectedMenuItem(
              location?.pathname
            );

            if (selectedMenu) {
              props.setMenuItem(selectedMenu);
            }
          }
        } catch (err) {
          console.warn(err, 'User session verification failed, redirecting to login.');
          loginRedirect(navigate);
        } finally {
          setLoading(false);
        }
      };

      verifyUserSession();
    }, []);



  if(!user){
    return Loading;
  }
  if (user) {
    return (
      <>
        {children}
      </>
    )
  }

  return null
}

const UnauthenticatedTemplate = ({
  children
}: {
  children: React.ReactNode
}) => {
  return <>{children}</>
}
