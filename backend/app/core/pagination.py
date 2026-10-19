from pydantic import BaseModel


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.page_size))


def clamp_page(page: int, page_size: int, *, max_page_size: int = 100) -> tuple[int, int, int]:
    page = max(1, page)
    page_size = min(max(1, page_size), max_page_size)
    offset = (page - 1) * page_size
    return page, page_size, offset
