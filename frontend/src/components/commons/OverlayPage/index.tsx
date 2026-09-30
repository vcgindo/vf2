import { SCOverlayPage } from "./style";

const OverlayPage = ({ onClick }: any) => {
  const handleClick = () => {
    onClick();
  };
  return <SCOverlayPage onClick={handleClick}></SCOverlayPage>;
};

export default OverlayPage;
