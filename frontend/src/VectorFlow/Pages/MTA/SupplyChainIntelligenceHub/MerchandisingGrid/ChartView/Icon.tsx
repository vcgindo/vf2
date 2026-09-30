export const StoreIcon = (props:{value:number,color?:string}) => {

    const {
      value,
      color = 'rgb(105, 105, 105)'
    } = props

    const getXOffset =(number:number):string=>{
      if(number<10)return '75%'
      if(10<=number && number<100)return '65%'
      return '55%'
    }
  
      return (
        <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 74.914 63.573">
          <g id="Group_10160" data-name="Group 10160" transform="translate(-23.543 -9)">
            <path id="Path_876" data-name="Path 876" d="M561.321,696.369H500.079V658.623h4.039V692.33h53.164V658.623h4.039Z" transform="translate(-469.7 -623.797)" fill={color}/>
            <path id="_9c5fe2e8308387bc681d48f000a3b7cb" data-name="9c5fe2e8308387bc681d48f000a3b7cb" d="M40.475,30.825,45.436,12H56.962V30.825ZM42.8,12H31.518a.288.288,0,0,0-.282.171L21.51,30.825H37.84ZM20.778,33.372a8.433,8.433,0,0,0,16.674,0H20.778Zm19.414,0a8.433,8.433,0,0,0,16.674,0H40.192Zm19.414,0a8.433,8.433,0,0,0,16.674,0H59.605ZM76,30.825,71.035,12H59.51V30.825Zm3.023,2.548a8.433,8.433,0,0,0,16.674,0H79.019ZM73.67,12H84.953a.288.288,0,0,1,.282.171l9.726,18.653H78.631Z" transform="translate(2.765 -3)" fill={color} fillRule="evenodd"/>
            <text x={getXOffset(value)} y="90%"  fontSize="18" fill={color}>{value}</text>
          </g>
        </svg>
      );
    };
  
  export const StoreHoveredIcon = (props:{value:number,color?:string})=>{
      const {
        color = 'rgb(105, 105, 105)',
        value
      } = props

      const getXOffset =(number:number):string=>{
        if(number<10)return '0'
        if(10<=number && number<100)return '-5'
        return '-10'
      }

      return (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          xmlnsXlink="http://www.w3.org/1999/xlink"
          width="40"
          height="40"
          viewBox="0 0 74.914 63.573"
        >
          <g
            id="Component_33_3"
            data-name="Component 33 – 3"
            transform="translate(-23 -10)"
          >
            <g
              transform="matrix(1, 0, 0, 1, -35, -25)"
              filter="url(#Rectangle_11834)"
            >
              <g
                id="Rectangle_11834-2"
                data-name="Rectangle 11834"
                transform="translate(35 25)"
                fill="#fff"
                stroke={color}
                stroke-width="1"
              >
                <rect width="119" height="100" rx="6" stroke="none" />
                <rect
                  x="0.5"
                  y="0.5"
                  width="118"
                  height="99"
                  rx="5.5"
                  fill="none"
                />
              </g>
            </g>
            <path
              id="Path_876"
              data-name="Path 876"
              d="M561.321,696.369H500.079V658.623h4.039V692.33h53.164V658.623h4.039Z"
              transform="translate(-469.7 -623.797)"
              fill={color}
            />
            <path
              id="_9c5fe2e8308387bc681d48f000a3b7cb"
              data-name="9c5fe2e8308387bc681d48f000a3b7cb"
              d="M40.475,30.825,45.436,12H56.962V30.825ZM42.8,12H31.518a.288.288,0,0,0-.282.171L21.51,30.825H37.84ZM20.778,33.372a8.433,8.433,0,0,0,16.674,0H20.778Zm19.414,0a8.433,8.433,0,0,0,16.674,0H40.192Zm19.414,0a8.433,8.433,0,0,0,16.674,0H59.605ZM76,30.825,71.035,12H59.51V30.825Zm3.023,2.548a8.433,8.433,0,0,0,16.674,0H79.019ZM73.67,12H84.953a.288.288,0,0,1,.282.171l9.726,18.653H78.631Z"
              transform="translate(2.765 -3)"
              fill={color}
              fillRule="evenodd"
            />
            <g
              id="Group_6153"
              data-name="Group 6153"
              transform="translate(-463.699 -601.834)"
            >
              <path
                id="Path_11099"
                data-name="Path 11099"
                d="M496.282,641.015h14.225"
                transform="translate(1.354 14.519)"
                fill="none"
                stroke={color}
                stroke-width="2"
              />
              <path
                id="Path_11102"
                data-name="Path 11102"
                d="M496.282,641.015h14.225"
                transform="translate(41.12 14.519)"
                fill="none"
                stroke={color}
                stroke-width="2"
              />
              <path
                id="Path_11098"
                data-name="Path 11098"
                d="M496.282,641.015h54.33"
                transform="translate(1.353 5.535)"
                fill="none"
                stroke={color}
                stroke-width="2"
              />
              <path
                id="Path_11101"
                data-name="Path 11101"
                d="M496.282,641.015h54.33"
                transform="translate(1.353 25.019)"
                fill="none"
                stroke={color}
                stroke-width="2"
              />
            </g>
            <text
              id="_60"
              data-name="60"
              transform="translate(55.101 60.199)"
              fill={color}
              font-size="18"
              font-family="Roboto-Medium, Roboto"
              font-weight="500"
            >
              <tspan x={getXOffset(value)} y="0">
                {value}
              </tspan>
            </text>
          </g>
        </svg>
      );
  }