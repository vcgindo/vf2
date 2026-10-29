import React from 'react';
import { act, renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import axios from 'axios';
import { useGetBTRData, useGetBTRDataCount } from './index';

jest.mock('axios');
const post = axios.post as jest.Mock;

test.each([['rows', useGetBTRData], ['counts', useGetBTRDataCount]] as const)(
    '%s forwards cancellation only as Axios options and retains plain payload calls', async (_name, useRequest) => {
        post.mockReset().mockResolvedValue({ data: { data: {} } });
        const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
        const wrapper = ({ children }: { children: React.ReactNode }) =>
            <QueryClientProvider client={client}>{children}</QueryClientProvider>;
        const { result, unmount } = renderHook(useRequest, { wrapper });
        const controller = new AbortController();
        const payload = { name: 'both', filters: {}, paginationParameter: { pageNumber: 1 } };
        await act(async () => { await result.current.mutateAsync({ ...payload, signal: controller.signal }); });
        expect(post.mock.calls[0][1]).toEqual(payload);
        expect(post.mock.calls[0][1]).not.toHaveProperty('signal');
        expect(post.mock.calls[0][2].signal).toBe(controller.signal);
        await act(async () => { await result.current.mutateAsync(payload); });
        expect(post.mock.calls[1][1]).toEqual(payload);
        expect(post.mock.calls[1][2].signal).toBeUndefined();
        unmount();
        client.clear();
    }
);
