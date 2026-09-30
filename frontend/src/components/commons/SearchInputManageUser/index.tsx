import { SearchWrapper, SearchInputManageUserStyled, SearchIcon } from './style';

const SearchInputManageUser = ({ searchUserBasedOn, setSearchUserBasedOn }: any) => {
    return (
        <SearchWrapper>
            <SearchInputManageUserStyled 
                placeholder="User Id"
                aria-label="Search components"
                id="search"
                type="text"
                value={searchUserBasedOn}
                onChange={(e) => setSearchUserBasedOn(e.target.value)} 
            />
            <SearchIcon>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20.002" viewBox="0 0 20 20.002" data-testid='vfmaster-search-icon'>
                    <g id="Group_3376" data-name="Group 3376" transform="translate(-905.1 -140.058)">
                        <g id="b995a33f0790c855384b59de531e8fe3" transform="translate(905.1 140.058)">
                            <path id="Path_90" data-name="Path 90" d="M16.352,24.4A8.152,8.152,0,1,1,24.5,16.252,8.163,8.163,0,0,1,16.352,24.4Zm0-15.093a6.982,6.982,0,1,0,6.982,6.982A6.994,6.994,0,0,0,16.352,9.312Z" transform="translate(-8.2 -8.1)" fill="#313131" />
                            <path id="Path_91" data-name="Path 91" d="M45.786,46.664,40.1,41.02l.92-.92,5.644,5.686-.878.878" transform="translate(-26.664 -26.662)" fill="#313131" />
                        </g>
                    </g>
                </svg>
            </SearchIcon>
        </SearchWrapper>
    );
}

export default SearchInputManageUser;
