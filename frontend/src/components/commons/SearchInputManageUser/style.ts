import styled from "styled-components"; 

export const SearchWrapper = styled.div`
    position: relative;
`;

export const SearchInputManageUserStyled = styled.input`
    width: 100%;
    height: 40px;
    border-radius: 40px;
    opacity: 1;
    padding: 0px 40px 0px 14px; /* Add padding to avoid overlap with the icon */
    background-color: #F2F2F2;
    outline: none;
    border: none;
    font-size: 16px;

`;

export const SearchIcon = styled.div`
    position: absolute;
    top: 50%;
    right: 14px;
    transform: translateY(-50%);
    width: 20px;
    height: 20px;
    pointer-events: none;
    

    svg {
        width: 100%;
        height: 100%;
        fill: #313131;
        
    }
`;
