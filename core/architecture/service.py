from typing import Type, TypeVar, Callable, Dict, Any
from fastapi import Depends
from inspect import Parameter, Signature

T = TypeVar("T", bound="AbstractService")


class AbstractService:
    """
    Base class for services, providing dynamic dependency injection capabilities for FastAPI.
    Subclasses define their required dependencies in the `DEPENDENCIES` class attribute.
    """

    # This class attribute will hold all dependencies for the service.
    # Subclasses should override this dictionary to define their specific dependencies.
    # Each entry should be a key-value pair where:
    # - Key (str): The name of the dependency parameter (e.g., "session", "settings").
    # - Value (Any): An Annotated type that includes the FastAPI Depends object
    #                (e.g., Annotated[AsyncSession, Depends(get_db)]).
    DEPENDENCIES: Dict[str, Any] = {}

    def __init__(self, **kwargs: Any):
        """
        Initialize the service with all its dependencies.
        Dependencies are passed as keyword arguments by FastAPI's injection system.

        :param kwargs: All dependencies resolved and injected by FastAPI.
        """
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def _get_combined_dependency_function(cls: Type[T], **kwargs: Any) -> T:
        """
        Internal method that acts as the target callable for FastAPI's Depends.
        It receives all resolved dependencies as keyword arguments and instantiates
        the service class with them.

        :param kwargs: All dependencies resolved by FastAPI based on the dynamic signature.
        :return: An instance of the service class (cls).
        """
        # Instantiate the service class, passing all resolved dependencies directly
        # to its __init__ method.
        return cls(**kwargs)

    @classmethod
    def get_dependency(cls: Type[T]) -> Callable[..., T]:
        """
        Returns a FastAPI dependency callable for this service.

        This method dynamically constructs a function signature based on the `DEPENDENCIES`
        class attribute of the current service class (cls). FastAPI inspects this signature
        to know which dependencies to resolve and inject.

        The returned callable, when used with `FastAPI.Depends()`, will ensure that
        all declared dependencies are resolved and passed to the service's constructor.

        :return: A callable suitable for use with FastAPI's `Depends()`.
        """
        parameters = []
        # Get the dependencies specific to the current class (cls).
        # `getattr` with a default ensures it works even if a subclass doesn't define DEPENDENCIES.
        current_class_deps = getattr(cls, "DEPENDENCIES", {})

        # Iterate through the declared dependencies to build the function signature.
        for name, annotated_type_with_depends in current_class_deps.items():
            parameters.append(
                Parameter(
                    name,
                    Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=annotated_type_with_depends,
                )
            )

        # Define a simple wrapper function. FastAPI will inspect its dynamically set signature.
        def dynamic_dependency_callable(**kwargs: Any) -> T:
            """
            Internal wrapper to collect resolved dependencies and pass them to the service.
            """
            return cls._get_combined_dependency_function(**kwargs)

        # IMPORTANT: Dynamically set the __signature__ of the wrapper function.
        # This is the crucial step that tells FastAPI what arguments (and thus, what dependencies)
        # `dynamic_dependency_callable` expects. Without this, FastAPI cannot resolve
        # the dependencies defined in the `DEPENDENCIES` class attribute.
        dynamic_dependency_callable.__signature__ = Signature(parameters)
        dynamic_dependency_callable.__name__ = f"_get_{cls.__name__.lower()}_service"
        return Depends(dynamic_dependency_callable)
