# Custom error classes used by the GeoScript interpreter
# base error class for the DSL
class GeoScriptError(Exception):
    def __init__(self, message: str, hint: str = "") -> None:
        # build error message
        full = f"[GeoScript] {message}"
        if hint:
            full += f"\nHint: {hint}"

        super().__init__(full)
        self.message = message
        self.hint = hint


# generic runtime error during execution
class GeoRuntimeError(GeoScriptError):
    pass


# raised when a variable or identifier is not found
class GeoNameError(GeoRuntimeError):
    def __init__(self, name: str) -> None:
        super().__init__(
            f"Undefined name '{name}'",
            hint="Maybe it was not declared.",
        )
        self.name = name


# raised when wrong type of value is used
class GeoTypeError(GeoRuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


# division by zero error
class GeoDivisionByZero(GeoRuntimeError):
    def __init__(self) -> None:
        super().__init__("Division by zero")


# constraint related error in geometry
class GeoConstraintError(GeoRuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


# incorrect number of arguments in a function
class GeoArgumentError(GeoRuntimeError):
    def __init__(self, func_name: str, expected: int, got: int) -> None:
        super().__init__(
            f"{func_name} expects {expected} arguments but got {got}"
        )


# raised when trying to modify immutable variable
class GeoImmutableError(GeoRuntimeError):
    def __init__(self, name: str) -> None:
        super().__init__(
            f"Cannot modify '{name}', it was not declared with let"
        )
        self.name = name


# assertion failure inside the DSL
class GeoAssertionError(GeoScriptError):
    def __init__(self, description: str) -> None:
        super().__init__(f"Assertion failed: {description}")
        self.description = description


# used internally to handle return statements in functions
class ReturnSignal(Exception):
    def __init__(self, value=None) -> None:
        super().__init__()
        self.value = value
