from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param, remove_query_param
from .models import CardSet
from .serializers import CardSetSerializer


SORT_OPTIONS = {
    "release_date_desc": ["-release_date", "name"],
    "release_date_asc": ["release_date", "name"],
    "name_asc": ["name"],
    "name_desc": ["-name"],
}

class CardSetViewSet(viewsets.ReadOnlyModelViewSet):
    class Pagination(PageNumberPagination):
        page_size = 18

        def get_paginated_response(self, data):
            page = self.page
            request = self.request
            return Response({
                "links": {
                    "first": self._page_link(1),
                    "last": self._page_link(page.paginator.num_pages),
                    "next": self.get_next_link(),
                    "prev": self.get_previous_link(),
                },
                "meta": {
                    "pagination": {
                        "page": page.number,
                        "pages": page.paginator.num_pages,
                        "count": page.paginator.count,
                    }
                },
                "results": data,
            })
        
        def _page_link(self, page_number):
            url = self.request.build_absolute_uri()
            if page_number == 1:
                return remove_query_param(url, self.page_query_param)
            return replace_query_param(url, self.page_query_param, page_number)


    queryset = CardSet.objects.all().order_by("-release_date", "name")
    serializer_class = CardSetSerializer
    pagination_class = Pagination

    def get_queryset(self):
        sort = self.request.query_params.get("sort", "release_date_desc")
        ordering = SORT_OPTIONS.get(sort, SORT_OPTIONS["release_date_desc"])
        return CardSet.objects.all().order_by(*ordering)
