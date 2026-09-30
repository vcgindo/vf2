import {render} from '@testing-library/react'
import VFMasterFieldSearch from '.'
import { UserDataContext } from '../../../../context';

const dummyFunction = jest.fn()

describe('VFMasterFieldSearch',()=>{
    it('Renders on the document',()=>{
        const {getByTestId} = render(<UserDataContext.Provider value={{user:{user:{theme_ui:'REGALBLAZE'}},changeColorTheme:(color) => {return color},isSideBarOpen:true,toggleSideBar:jest.fn}}><VFMasterFieldSearch value={[]} setValue={dummyFunction} options={[]} placeholder='Search' maxToShow={3} backgroundColor='white' handleListChild={dummyFunction} disabled={false} /></UserDataContext.Provider>)
        expect(getByTestId('search-wrapper')).toBeInTheDocument()
    })
})