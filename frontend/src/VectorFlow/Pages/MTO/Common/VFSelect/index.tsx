import Select from 'react-select';
import { chooseThemeColor } from '../../../../../styles/global';


const VFSelect = ({ options, themeUi, icon, placeholder, ...rest }: any) => {

    const SearchIcon = () => {
        return (
            <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 20 20.002" data-testid='vfmaster-search-icon'>
                <g id="Group_3376" data-name="Group 3376" transform="translate(-905.1 -140.058)">
                    <g id="b995a33f0790c855384b59de531e8fe3" transform="translate(905.1 140.058)">
                        <path id="Path_90" data-name="Path 90" d="M16.352,24.4A8.152,8.152,0,1,1,24.5,16.252,8.163,8.163,0,0,1,16.352,24.4Zm0-15.093a6.982,6.982,0,1,0,6.982,6.982A6.994,6.994,0,0,0,16.352,9.312Z" transform="translate(-8.2 -8.1)" fill="#313131" />
                        <path id="Path_91" data-name="Path 91" d="M45.786,46.664,40.1,41.02l.92-.92,5.644,5.686-.878.878" transform="translate(-26.664 -26.662)" fill="#313131" />
                    </g>
                </g>
            </svg>
        )
    }
    return (
        <Select
            isSearchable={true}
            components={{
                IndicatorSeparator: () => null,
                DropdownIndicator: icon ? SearchIcon : null
            }}
            menuPlacement={"auto"}
            // menuIsOpen={true}
            styles={{
                container: (base) => ({
                    ...base,
                    width: placeholder == "Select Order Type" ? 170 : "100%"
                }),
                control: (base: any, state: any) => ({
                    ...base,
                    minHeight: "25px",
                    minWidth: "80px",
                    boxShadow: state.isFocused ? 0 : 0,
                    border: "1px solid hsl(0, 0%, 80%) !important",
                    '&:hover': {
                        border: "1px solid hsl(0, 0%, 80%)"
                    }
                }),
                menu: (base) => ({
                    ...base,
                    zIndex: "100000000",
                    minWidth: "100%",
                    width: "max-content"
                }),
                menuList: (base) => ({
                    ...base,
                    maxHeight: "120px"
                }),
                dropdownIndicator: (base) => ({
                    ...base,
                    color: "grey",
                    padding: "0"
                }),
                clearIndicator: (base) => ({
                    ...base,
                    color: "grey",
                    padding: "0"
                }),
                indicatorsContainer: (base) => ({
                    ...base,
                    padding: "0 8px"
                })
            }}
            theme={(theme) => ({
                ...theme,
                borderRadius: 0,
                colors: {
                    ...theme.colors,
                    primary50: chooseThemeColor[themeUi].color4,
                    primary25: chooseThemeColor[themeUi].color4 + "4A",
                    primary: chooseThemeColor[themeUi].color4,
                },
            })}
            // menuIsOpen
            options={options}
            {...rest}

        />
    )
}

export default VFSelect