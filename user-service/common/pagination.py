class Paginator:
    def __init__(self, request, result_len=None):
        self.request = request
        query_params = request.query_params
        self.page = int(query_params.get("page", 1))
        self.per_page = int(query_params.get("per_page", 10))
        self.result_len = result_len

    @property
    def offset(self):
        return (self.page - 1) * self.per_page

    @property
    def start_index(self):
        return self.offset

    @property
    def end_index(self):
        return self.offset + self.per_page

    def set_result_len(self, result_len):
        self.result_len = result_len

    def get_paginated_response(self):
        if self.result_len is None:
            return {}

        number_pages = self.result_len / self.per_page
        if number_pages > int(number_pages):
            number_pages = int(number_pages) + 1

        in_page = self.per_page
        if self.page < number_pages:
            in_page = self.per_page
        elif self.page == number_pages:
            in_page = self.result_len - self.per_page*(number_pages-1)
        elif self.page > number_pages:
            in_page = 0

        return {
            'links': {
                'url': self.request.get_full_path(),
            },
            "page": self.page,
            "number_pages": number_pages,
            "in_page": in_page,
            "total": self.result_len
        }
