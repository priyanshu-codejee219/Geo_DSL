# basic error classes used in interpreter

class GeoScriptError(Exception):
    # base class for all errors
    def __init__(self, message: str, hint: str = "") -> None:
        full = f"[GeoScript] {message}"
        if hint:
            full += f"\nHint: {hint}"
        super().__init__(full)
        self.message = message
        self.hint = hint

# general error during execution
class GeoRuntimeError(GeoScriptError):
    pass

# error when variable is not found
class GeoNameError(GeoRuntimeError):
    def __init__(self, name: str) -> None:
        super().__init__(
            f"Undefined name '{name}'",
            hint="Declare it first",
        )
        self.name = name

# error when wrong type is used
class GeoTypeError(GeoRuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)

# error for division by zero
class GeoDivisionByZero(GeoRuntimeError):
    def __init__(self) -> None:
        super().__init__("Division by zero")

# error for invalid constraints
class GeoConstraintError(GeoRuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)

# error when arguments are wrong
class GeoArgumentError(GeoRuntimeError):
    def __init__(self, func_name: str, expected: int, got: int) -> None:
        super().__init__(
            f"{func_name} expects {expected} arguments but got {got}"
        )

# error when trying to change fixed variable
class GeoImmutableError(GeoRuntimeError):
    def __init__(self, name: str) -> None:
        super().__init__(
            f"Cannot modify '{name}', not declared with let"
        )
        self.name = name

# error when assert fails
class GeoAssertionError(GeoScriptError):
    def __init__(self, description: str) -> None:
        super().__init__(f"Assertion failed: {description}")
        self.description = description

# used to return value from function
class ReturnSignal(Exception):
    def __init__(self, value=None) -> None:
        super().__init__()
        self.value = value
