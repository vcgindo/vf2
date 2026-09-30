
import {  useEffect, useRef } from 'react';

export function useIdleTimer(onIdle: () => void, timeout: number) {

  const timerRef = useRef<number | null>(null);

  const resetTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    timerRef.current = window.setTimeout(onIdle, timeout);
  };

  useEffect(() => {
    const eventsToListenFor: (keyof WindowEventMap)[] = [
      'mousemove',
      'mousedown',
      'keypress',
      'touchstart',
      'scroll',
    ];

    const handleActivity = () => {
      resetTimer();
    };

    eventsToListenFor.forEach((event) => {
      window.addEventListener(event, handleActivity);
    });

    resetTimer();

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      eventsToListenFor.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
    };
  }, [onIdle, timeout]); 
  return { resetTimer }; 
}