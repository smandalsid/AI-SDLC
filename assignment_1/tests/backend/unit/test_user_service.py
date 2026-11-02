from collections.abc import Sequence

from app.models.user import User
from app.services.user_service import UserService


class FakeUserReader:
    def __init__(self, users: list[User]) -> None:
        self.users = users

    def list_page(self, page: int, page_size: int) -> Sequence[User]:
        start = (page - 1) * page_size
        return self.users[start : start + page_size]

    def count(self) -> int:
        return len(self.users)

    def get(self, user_id: int) -> User | None:
        return next((user for user in self.users if user.id == user_id), None)


def make_service() -> UserService:
    users = [User(id=1, name="Asha"), User(id=2, name="Ravi"), User(id=3, name="Meera")]
    return UserService(FakeUserReader(users))


def test_list_returns_a_page_with_the_total() -> None:
    result = make_service().list_users(page=2, page_size=2)

    assert [(user.id, user.name) for user in result.items] == [(3, "Meera")]
    assert (result.page, result.page_size, result.total) == (2, 2, 3)


def test_first_page_holds_users_in_order() -> None:
    result = make_service().list_users(page=1, page_size=20)

    assert [user.name for user in result.items] == ["Asha", "Ravi", "Meera"]
