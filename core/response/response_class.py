from typing import Any
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel


class CustomORJSONResponse(ORJSONResponse):
    def render(self, content: Any) -> bytes:
        def clean(obj):
            if isinstance(obj, BaseModel):
                return {
                    "id" if k == "_id" else k: clean(v)
                    for k, v in obj.model_dump().items()
                }
            elif isinstance(obj, dict):
                return {"id" if k == "_id" else k: clean(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean(i) for i in obj]
            elif isinstance(obj, tuple):
                return tuple(clean(i) for i in obj)
            else:
                return obj

        cleaned_content = clean(content)
        return super().render(cleaned_content)
