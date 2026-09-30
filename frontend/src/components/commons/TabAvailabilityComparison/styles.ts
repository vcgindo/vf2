import styled from 'styled-components'
import * as gridSystem from '../../../styles/gridSystem'

export const ContentArea = styled.div`
  display: block;

  .loading {
    margin: 26vh auto;
  }
`

export const ContentItem = styled.div<{ color: string }>`
  display: flex;
  border: ${(props) =>
      props.color === 'Red' ? '4px' : props.color === 'White' ? '4px' : '2px'}
    solid
    ${(props) =>
      props.color === 'Red'
        ? '#6C4E0A'
        : props.color === 'White'
        ? '#6C4E0A'
        : '#CCCCCC'};
  border-radius: 6px;
  margin: 6px 12px;
  position: relative;

  .left-icon {
    position: absolute;
    left: -54px;
    top: 45px;
    z-index: 1;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      left: -39px;
      top: 33px;
      height: 8vw;
    }
  }
`

export const ItemPanelLoading = styled.div`
  display: inline;

  .overlay {
    background: #ddd;
    position: absolute;
    z-index: 1;
    opacity: 0.7;
    height: 100%;
    width: 100%;
  }

  .loading {
    margin: 0;
    position: absolute;
    z-index: 1;
    height: 100%;
    width: 100%;
  }
`

export const ItemPanel = styled.div`
  cursor: pointer;
  display: block;
  background: #ffffff 0% 0% no-repeat padding-box;
  box-shadow: 0px 14px 20px #b4b4b429;
  border: 0.5px solid #cccccc;
  margin: 1.2rem 1.2rem 4.2rem 1.2rem;
  flex: 1 0;
  position: relative;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    margin: 0.5rem 0.5rem 3rem 0.5rem;
  }

  :hover {
    border: 1px solid #820f4c;
  }

  .number-last {
    position: absolute;
    color: #820f4c;
    font-size: 1.5rem;
    font-weight: bold;
    border: 0.3px solid #820f4c;
    background: #ffffff 0% 0% no-repeat padding-box;
    border-radius: 3px;
    padding: 0 10px;
    bottom: -4px;
    left: -4px;
    z-index: 2;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      padding: 0 6px;
      font-size: 1.1rem;
    }
  }
`

export const ItemPanelHeader = styled.div`
  display: block;
  position: relative;

  img {
    background: #ffffff 0% 0% no-repeat padding-box;
    border: 0.4px solid #cccccc;
    border-radius: 3px;
    padding: 5px 8px;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      height: 2.5rem;
    }
  }
`

export const ItemPanelHeaderContent = styled.div<{
  index: number
  color: string
}>`
  display: flex;

  span {
    flex: 1 0;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 67px;
    font-size: 2rem;
    font-weight: bold;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      height: 4vw;
      font-size: 1.5rem;
    }
  }
  span:nth-child(1) {
    background: ${(props) =>
        props.index === 0
          ? 'rgba(255, 231, 231, .35)'
          : props.index === 1
          ? 'rgba(230, 255, 232, .35)'
          : '#FFFFFF'}
      0% 0% no-repeat padding-box;
    color: ${(props) =>
      props.index === 0
        ? '#EA0F0F'
        : props.index === 1
        ? '#096912'
        : '#292C2E'};
  }
  span:nth-child(2) {
    border-left: 0.5px solid #cccccc;
    background: ${(props) =>
        props.color === 'Red'
          ? 'rgba(255, 231, 231, .35)'
          : props.color === 'Green'
          ? 'rgba(230, 255, 232, .35)'
          : '#FFFFFF'}
      0% 0% no-repeat padding-box;
    color: ${(props) =>
      props.color === 'Red'
        ? '#EA0F0F'
        : props.color === 'Green'
        ? '#096912'
        : '#292C2E'};
  }
`

export const ItemPanelBody = styled.div`
  display: flex;
  position: relative;
  margin-bottom: 1.5rem;
`

export const ItemPanelBodyLeft = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1 0;
  flex-flow: column;

  .rep-in,
  .ist-in {
    position: relative;
    margin: 1.5rem 0 1.5rem 0;
    display: inherit;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      margin: 1rem 0 1rem 0;
    }

    span {
      background: #ffffff 0% 0% no-repeat padding-box;
      border: 0.4px solid #cccccc;
      font-size: 1.4rem;
      font-weight: 500;
      padding: 3px 10px 0px 10px;

      @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
          .size.laptopL}) {
        font-size: 1rem;
        padding: 2px 7px 0 6px;
      }

      sub {
        font-size: 1rem;

        @media (min-width: ${gridSystem.size
            .laptop}) and (max-width: ${gridSystem.size.laptopL}) {
          font-size: 0.6rem;
        }
      }
    }
  }

  .rep-in::after {
    content: "REP IN";
    position: absolute;
    color: #820f4c;
    font-size: 1rem;
    font-weight: bold;
    background: #ffedf7 0% 0% no-repeat padding-box;
    border: 0.3px solid #820f4c;
    border-radius: 0px 0px 2px 2px;
    padding: 0 5px;
    bottom: -17px;
    right: 0;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      font-size: 0.6rem;
      bottom: -11px;
    }
  }

  .ist-in::after {
    content: "IST IN";
    position: absolute;
    color: #820f4c;
    font-size: 1rem;
    font-weight: bold;
    background: #ffedf7 0% 0% no-repeat padding-box;
    border: 0.3px solid #820f4c;
    border-radius: 0px 0px 2px 2px;
    padding: 0 5px;
    bottom: -17px;
    right: 0;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      font-size: 0.6rem;
      bottom: -11px;
    }
  }
`

export const ItemPanelBodyCenter = styled.div<{ activeTab: string }>`
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0;

  .store {
    display: flex;
    align-items: center;
    justify-content: center;
    background: #ffffff 0% 0% no-repeat padding-box;
    box-shadow: inset 3px 3px 6px #76767648;
    border: 0.5px solid #cccccc;
    border-radius: 6px;
    height: 58px;
    width: 65px;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      height: 45px;
      width: 49px;
    }

    img {
      margin-top: ${(props) => (props.activeTab !== 'store' ? '7' : '0')}px;
      margin-left: ${(props) => (props.activeTab !== 'store' ? '7' : '0')}px;

      @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
          .size.laptopL}) {
        width: ${(props) => (props.activeTab !== 'store' ? '2.5' : '2')}vw;
      }
    }
  }

  .gray-arrow {
    width: 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
  }
`

export const ItemPanelBodyRight = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1 0;
  flex-flow: column;

  .ist-out {
    position: relative;
    margin: 1.5rem 0 1.5rem 0;
    display: inherit;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      margin: 1rem 0 1rem 0;
    }

    span {
      background: #ffffff 0% 0% no-repeat padding-box;
      border: 0.4px solid #cccccc;
      font-size: 1.4rem;
      font-weight: 500;
      padding: 3px 10px 0px 10px;

      @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
          .size.laptopL}) {
        font-size: 1rem;
        padding: 2px 7px 0 6px;
      }

      sub {
        font-size: 1rem;

        @media (min-width: ${gridSystem.size
            .laptop}) and (max-width: ${gridSystem.size.laptopL}) {
          font-size: 0.6rem;
        }
      }
    }
  }

  .ist-out::after {
    content: "IST OUT";
    position: absolute;
    color: #820f4c;
    font-size: 1rem;
    font-weight: bold;
    background: #ffedf7 0% 0% no-repeat padding-box;
    border: 0.3px solid #820f4c;
    border-radius: 0px 0px 2px 2px;
    padding: 0 5px;
    bottom: -17px;
    right: 0;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      font-size: 0.6rem;
      bottom: -11px;
    }
  }
`

export const ItemPanelFooter = styled.div`
  position: absolute;
  right: -1px;
  bottom: -31px;
  border-radius: 0 0 6px 6px;
  background: #ffffff 0% 0% no-repeat padding-box;
  border: 0.5px solid #bbbfc6;
  display: flex;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    bottom: -21.4px;
  }

  span:nth-child(1):after {
    content: "";
    border-left: 0.5px solid #bbbfc6;
    position: absolute;
    right: 0;
    height: 70%;
  }

  span {
    font-size: 1.4rem;
    font-weight: 500;
    padding: 4px 10px 1px 10px;
    position: relative;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      font-size: 1rem;
      padding: 2px 5px 1px 8px;
    }

    sub {
      font-size: 1rem;

      @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
          .size.laptopL}) {
        font-size: 0.6rem;
      }
    }
  }

  img {
    margin: 0 0 0 5px;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      width: 0.8vw;
    }
  }
`

export const ProjectedAvailability = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  transform: matrix(0, -1, 1, 0, 0, 0);
  position: absolute;
  left: -162px;
  top: 100px;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.laptopL}) {
    left: -135px;
    top: 75px;
  }

  span {
    font-size: 2rem;
    font-weight: 500;
    border: 0.5px dashed rgba(18, 20, 24, 0.5);
    padding: 5px 15px;
    border-radius: 3px;
    text-align: center;

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.laptopL}) {
      font-size: 1.6rem;
    }

    p:nth-child(2) {
      font-size: 1.3rem;

      @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
          .size.laptopL}) {
        font-size: 0.9rem;
      }
    }
  }
`
