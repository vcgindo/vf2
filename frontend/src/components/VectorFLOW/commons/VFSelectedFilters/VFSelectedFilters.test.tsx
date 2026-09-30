import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react';
import VFSelectedFilters from './';
import { BPRFilterState } from '../../../../VectorFlow/types/BPR';

// Mock props for testing
const mockFilters:BPRFilterState = {
    supplyChainFilter: {
        id: 'supplyChainFilterId',
        label: 'Supply Chain',
        filters: [
            { name: 'filter1', attributeName: 'Attribute 1',label:'label', value: 'Value 1',operator:">" },
            { name: 'filter2', attributeName: 'Attribute 2',label:'label', value: 'Value 2',operator:"<"  }
        ]
    },
    locationFilter: {
        id: 'locationFilterId',
        label: 'Location',
        filters: []
    },
    productFilter:{
        id:'3',
        label:'Product',
        filters:[]
    },
    availabilityFilter:{
        id:'4',
        label:'Availability',
        // filters:[
        //     {
        //         name:"1",
        //         attributeName:"ETC",
        //         operator:'equalTo',
        //         value:'yellow'
        //     },
        //     {
        //         name:"2",
        //         attributeName:"ETC",
        //         operator:'equalTo',
        //         value:'black'
        //     },
        //     {
        //         name:"3",
        //         attributeName:"ETC",
        //         operator:'equalTo',
        //         value:'green'
        //     }
        // ]
            filters: [
            {
                "attributeName": "Norm",
                "value": "22",
                "operator": "equalto",
                "label": "Norm",
                "name": "AF1"
            },
            {
                "attributeName": "Stock",
                "value": "10",
                "operator": "greaterthanequalto",
                "label": "Stock",
                "name": "AF2"
            }
        ]
    },
    colorFilter:{
        id:'5',
        label:'Color',
        filters:[]
    },
    coverageFilter:{
        id:'6',
        label:'Coverage',
        filters:[]
    },
    generalFilter:{
        id:'7',
        label:'General',
        filters:[]
    },
    customAttributeFilter:{
        id:'8',
        label:'Attribute',
        filters:[]
    },
    horizonFilter:{
        id:'9',
        label:'Horizon',
        filters:[]
    }
};

describe('VFSelectedFilters Component', () => {
    it('renders correctly with filters', () => {
        const onRemoveFilter = jest.fn();
        render(
            <VFSelectedFilters filters={mockFilters} onRemoveFilter={onRemoveFilter} />
        );
       


        // Check if the placeholder text is rendered
        expect(screen.getByText('Selected Filters')).toBeInTheDocument();

        // Check if the filter labels and values are rendered
        expect(screen.getByText(/supply chain:/i)).toBeInTheDocument();
        // expect(screen.getByText(/attribute 1/i)).toBeInTheDocument();
        // expect(screen.getByText(/attribute 2/i)).toBeInTheDocument();

        // Check if the close icon is rendered
        const closeIcon = screen.getAllByTestId('closeIcon-filter')[0]; // Adjust the test ID according to your implementation
        expect(closeIcon).toBeInTheDocument();

        // Simulate click on the close icon and check if the handler is called
        fireEvent.click(closeIcon);
        expect(onRemoveFilter).toHaveBeenCalledWith('supplyChainFilterId', 'filter1',"Value 1");
    });

    // Add more test cases for different scenarios as needed
});
