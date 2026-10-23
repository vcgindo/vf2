import React, { type PropsWithChildren, useEffect, useRef, useState } from 'react'
import {clearRedirecting, loginRedirect } from '../../../helpers/utils'
import { MainService } from '../../../module-main/services/api'
import { useLocation, useNavigate } from 'react-router'
import { useUserData } from '../../../context';
import { listMenuParent } from "../NavbarMenu/listMenu";
import { markStartup } from '../../../performance/screenProbe';
import { useDispatch } from 'react-redux';
import { MDMService } from '../../../VectorFlow/Services/MTA/MDM/api';
import { UPDATE_ENV_CONFIG } from '../../../redux/actions/MTA';

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
  const [profileVerified, setProfileVerified] = useState(false);
  const profileReady = profileVerified && Boolean(user);
  const configurationRequested = useRef(false);
  const dispatch = useDispatch();

  const navigate = useNavigate();
  const location = useLocation()
   
    useEffect(() => {
      let active = true;
      const verifyUserSession = async () => {
        try {
          // A protected-route verification is a new redirect transition. Any
          // failure below still goes through loginRedirect's deduplication.
          clearRedirecting();
          markStartup('profile-call');
          const response = await MainService.getProfile();
          if (!active) return;
          markStartup('profile-return');
          const profile = response?.data?.data;

          if (!profile) {
            throw new Error('Profile response did not include user data.');
          }

          setUser(profile);
          setProfileVerified(true);
          markStartup('profile-set-user');

          const selectedMenu = getSelectedMenuItem(
            location?.pathname
          );

          if (selectedMenu) {
            props.setMenuItem(selectedMenu);
          }
        } catch (err) {
          if (!active) return;
          console.warn(err, 'User session verification failed, redirecting to login.');
          loginRedirect(navigate);
        }
      };

      verifyUserSession();
      return () => { active = false; };
    }, []);

    useEffect(() => {
      if (!profileReady || configurationRequested.current) return;
      configurationRequested.current = true;
      let active = true;
      const getAllEnvironmentConfiguration = async () => {
        try {
          const response = await MDMService.getAllEnvironmentConfiguration();
          if (!active) return;
          const configMap = response?.data?.data.reduce((map: any, item: any) => {
            map[item.ConfigKey] = item.ConfigValue;
            return map;
          }, {});
          dispatch(UPDATE_ENV_CONFIG(configMap));
        } catch (err) {
          if (active) console.error("Unexpected error in get Environment configuration:", err);
        }
      };
      getAllEnvironmentConfiguration();
      return () => { active = false; };
    }, [profileReady, dispatch]);



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
