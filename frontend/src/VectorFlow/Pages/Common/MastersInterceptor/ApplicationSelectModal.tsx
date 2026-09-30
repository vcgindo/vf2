import React, { useEffect, useRef } from 'react';
import styled from 'styled-components';
import { useNavigate } from 'react-router-dom'; // Use 'react-router-dom'
import { useUserData } from '../../../../context';

const Container = styled.div<{ theme: string }>`
  display: flex;
  flex-direction: column;
  gap: 16px;
  font-family: 'Roboto';
  background: white;
  padding: 40px 60px;
  border-radius: 16px;
  box-shadow: 0 2px 3px rgba(0, 0, 0, 0.1);
`;

const OptionCard = styled.div<{ theme: string }>`
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 26px;
  border: 2px solid #f0f0f0;
  border-radius: 8px;
  box-shadow: 0 2px 3px rgba(0, 0, 0, 0.1);
  background-color: #fff;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  &:hover {
    transform: translateY(-2px);
    background: ${(props) =>
      props.theme === 'REGALBLAZE' ? `rgb(250, 246, 240)` : `rgba(128, 0, 64, 0.3)`};
  }
`;

const Icon = styled.div<{ theme: string }>`
  width: 45px;
  height: 45px;
  background-color: ${(props) =>
    props.theme === 'REGALBLAZE' ? `#FFEED3` : '#ffe0f0'};
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  img {
    position: absolute;
    top: 20%;
    left: 30%;
    width: 40px;
    height: 40px;
  }
`;

const Text = styled.div<{ theme: string }>`
  font-size: 14px;
  font-weight: 500;
  color: ${(props) =>
    props.theme === 'REGALBLAZE' ? `#C7810E` : `rgb(128, 0, 64)`};
`;

const ActionSelectModal = ({ redirectUrl }: any) => {
  const navigate = useNavigate();
  const { user } = useUserData();
  const themeUi = user.user.theme_ui;

  const ref = useRef<{ appData: Array<{ text: string; icon: string; link: string }> }>({
    appData: []
  });


    const urlPermissionStr = user?.url_permission??[];
    const urlPermissionArr = urlPermissionStr || [];

  const updateAppData = (theme: any) => {
    const allOptions = [
      { text: 'Make to Availability (MTA)', icon: theme === "REGALBLAZE" ? '/assets/img/planning1.svg' : '/assets/img/planning.svg', link:"/mta"+ redirectUrl },
      { text: 'Make to Order (MTO)', icon: theme === "REGALBLAZE" ? '/assets/img/Prod-icon1.svg' : '/assets/img/Prod-icon.svg', link: "/mto" + redirectUrl },
      { text: 'Inter Store Transfer (IST)', icon: theme === "REGALBLAZE" ? '/assets/img/IST 2.svg' : '/assets/img/IST 1.svg', link:"/ist"+ redirectUrl },
    ];
  
    ref.current.appData = allOptions.filter(option => urlPermissionArr.includes(option.link));
    if (ref.current.appData.length === 0) {
      ref.current.appData.push(allOptions[0]);
    }
  };
  updateAppData(themeUi)

  useEffect(() => {
    if (urlPermissionArr.length > 0) {
      const urlPermission = urlPermissionArr.find((item: any) => item.url === redirectUrl);
      if (urlPermission?.permission === 'read') {
        ref.current.appData = ref.current.appData.filter((item: any) => item.text !== 'Make to Order (MTO)');
      }
    }
      
    // Auto-redirect if only one option remains
    if (ref.current.appData.length === 1) {
      navigate(ref.current.appData[0].link);
    }
  }, [urlPermissionArr, redirectUrl, navigate]);
  


  return (
    <Container theme={themeUi}>
      <span style={{ fontSize: '16px', fontWeight: 'bold', fontFamily: 'Roboto' }}>Select Application</span>
      {ref.current.appData.length > 0 ? (
      ref.current.appData.map((option, index) => (
        <OptionCard theme={themeUi} key={index} onClick={() => { navigate(option.link); }}>
          <Icon theme={themeUi}>
            <img src={option.icon} alt={option.text} />
          </Icon>
          <Text theme={themeUi}>{option.text}</Text>
        </OptionCard>
      ))
    ) : (
      <div>Loading...</div> // Replace with any loading component or SVG
    )}
    </Container>
  );
};

const ApplicationSelectModal = ({ redirectUrl }: any) => {
  return (
    <div style={{ paddingTop: '40px', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ height: '40%', width: '52%' }}>
        <ActionSelectModal redirectUrl={redirectUrl} />
      </div>
    </div>
  )
}

export default ApplicationSelectModal;