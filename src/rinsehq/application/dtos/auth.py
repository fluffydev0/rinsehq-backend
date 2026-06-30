from typing import List, Optional, Union
from dataclasses import dataclass
import re

from rinsehq.application.dtos.common import ErrorResult, Result, SuccessResult
from rinsehq.domain.entities.user import User

EMAIL_PATTERN = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


@dataclass(frozen=True)
class SignUpInput:
    email: str
    password: str
    name: Optional[str] = None


@dataclass(frozen=True)
class SignInInput:
    email: str
    password: str


def validate_sign_up(input: SignUpInput) -> Union[Result[SignUpInput], ErrorResult]:
    email = input.email.strip().lower()
    if not EMAIL_PATTERN.match(email):
        return ErrorResult("Enter a valid email address")
    if len(input.password) < 8:
        return ErrorResult("Password must be at least 8 characters")
    return SuccessResult(SignUpInput(email=email, password=input.password, name=input.name))


def validate_sign_in(input: SignInInput) -> Union[Result[SignInInput], ErrorResult]:
    email = input.email.strip().lower()
    if not EMAIL_PATTERN.match(email):
        return ErrorResult("Enter a valid email address")
    if not input.password:
        return ErrorResult("Password is required")
    return SuccessResult(SignInInput(email=email, password=input.password))
