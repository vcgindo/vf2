import { useState, useRef, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { MainService } from '../../../../../module-main/services/api';
import { useIdleTimer } from './useIdleTimer';
import { notifyLoader } from '../../../../../helpers/notify';
import { toast } from 'react-toastify';
import { useUserData } from '../../../../../context';

export function AutoLogoutTimer() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const location = useLocation();

  const [isWarningVisible, setWarningVisible] = useState(false);
  const finalLogoutTimerRef = useRef<number | null>(null);
  const { user, setUser } = useUserData();
  
  const logoutTimeout = parseInt(user?.config_data?.IDLE_TIMEOUT || '900000', 10);
  const promptDuration = 60 * 1000;
  const promptTimeout = logoutTimeout - promptDuration;

  const [activeApiRequests, setActiveApiRequests] = useState(0);
  const isApiActive = activeApiRequests > 0;

  
  const handlePromptLogicRef = useRef<any>();

  const stablePromptCallback = useCallback(() => {
    handlePromptLogicRef.current?.();
  }, []);

  const { resetTimer } = useIdleTimer(stablePromptCallback, promptTimeout);

  const performLogout = useCallback(async () => {
    if (location.pathname !== '/login') {
      toast.dismiss();
      setWarningVisible(false);
      const response = await MainService.logout(true, queryClient);
      if (response?.status == 204) {
        setUser(undefined);
      }
      navigate('/login');
    }
  }, [location.pathname, navigate, queryClient, setUser]); 


  const handlePromptLogic = useCallback(() => {
    if (isApiActive) {
      resetTimer();
      return;
    }

    if (location.pathname !== '/login') {
      setWarningVisible(true);
      notifyLoader('You will be logged out in a minute due to inactivity.');
      finalLogoutTimerRef.current = window.setTimeout(performLogout, promptDuration);
    }
  }, [
    isApiActive, 
    resetTimer,  
    location.pathname, 
    performLogout, 
    promptDuration
  ]);

  useEffect(() => {
    handlePromptLogicRef.current = handlePromptLogic;
  }, [handlePromptLogic]);

  const stayActive = useCallback(() => {
    setWarningVisible(false);
    toast.dismiss();
    if (finalLogoutTimerRef.current) {
      clearTimeout(finalLogoutTimerRef.current);
    }
    resetTimer();
  }, [resetTimer]); 

  useEffect(() => {
    const handleActivity = () => {
      if (isWarningVisible) {
        stayActive();
      }
    };

    const events: (keyof WindowEventMap)[] = ['mousemove', 'mousedown', 'keypress', 'touchstart', 'scroll'];
    events.forEach((event) => window.addEventListener(event, handleActivity));
        
    return () => {
      events.forEach((event) => window.removeEventListener(event, handleActivity));
    };
  }, [isWarningVisible, stayActive]);

  useEffect(() => {
    const handleApiStart = () => {
      setActiveApiRequests((count) => count + 1);
    };
    const handleApiEnd = () => {
      setActiveApiRequests((count) => Math.max(0, count - 1));
    };

    window.addEventListener('api-request-start', handleApiStart);
    window.addEventListener('api-request-end', handleApiEnd);

    return () => {
      window.removeEventListener('api-request-start', handleApiStart);
      window.removeEventListener('api-request-end', handleApiEnd);
    };
  }, []);

  return null;

}