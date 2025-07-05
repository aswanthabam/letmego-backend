from typing import Annotated
from core.architecture.service import AbstractService


class UserService(AbstractService):
    def __init__(self, session):
        super().__init__(session)


UserServiceDependency = Annotated[UserService, UserService.get_dependency()]
