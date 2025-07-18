from uuid import UUID


def is_valid_uuid(value: str, version=4) -> bool:
    if isinstance(value, str):
        try:
            val = UUID(value)
            if str(val) == value and val.version == version:
                return True
        except ValueError:
            pass
        return False
    elif isinstance(value, UUID):
        return value.version == version
    return False
