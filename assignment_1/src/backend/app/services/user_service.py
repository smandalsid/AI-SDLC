from app.repositories.protocols import UserReader
from app.services.types import PageResult, UserSummary


class UserService:
    def __init__(self, users: UserReader) -> None:
        self.users = users

    def list_users(self, page: int, page_size: int) -> PageResult[UserSummary]:
        items = [
            UserSummary(id=user.id, name=user.name)
            for user in self.users.list_page(page, page_size)
        ]
        return PageResult(items=items, page=page, page_size=page_size, total=self.users.count())
