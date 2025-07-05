from typing_extensions import Annotated
from core.architecture.service import AbstractService


class ChatService(AbstractService):
    def __init__(self, session):
        super().__init__(session)


ChatServiceDependency = Annotated[ChatService, ChatService.get_dependency()]
