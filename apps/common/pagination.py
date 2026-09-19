from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Lets the frontend ask for bigger pages, with a sane ceiling."""

    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 200
