# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import enum
from typing import Any, NamedTuple, Optional, Callable, TypeVar, ParamSpec

from dfacto.backend.db import session_factory

P = ParamSpec('P')
T = TypeVar('T')


class CommandException(Exception):
    """Base command exception."""


class RejectedCommand(CommandException):
    """Indicates that the command is rejected."""


class FailedCommand(CommandException):
    """Indicates that the command has failed."""


class CommandStatus(enum.Enum):
    """Authorized status of a command in its command report.

    REJECTED: the command cannot be satisfied.
    IN_PROGRESS: the command is running.
    COMPLETED : The command has terminated with success.
    FAILED: The command has terminated with errors.
    """

    REJECTED = enum.auto()
    IN_PROGRESS = enum.auto()
    COMPLETED = enum.auto()
    FAILED = enum.auto()


class CommandReport(NamedTuple):
    status: CommandStatus
    reason: Optional[str] = None

    def __repr__(self) -> str:
        reason = f", {self.reason}" if self.reason else ""
        return f"CommandReport({self.status.name}{reason})"


class CommandResponse(NamedTuple):
    """To be returned by any model's commands.

    Class attributes:
        status: the command status as defined above.
        reason: a message to explicit the status.
        body: an object returned by the command.
    """

    status: CommandStatus
    reason: Optional[str] = None
    body: Any = None

    def __repr__(self) -> str:
        reason = f", {self.reason}" if self.reason else ""
        return f"CommandResponse({self.status.name}{reason})"

    @property
    def report(self) -> CommandReport:
        return CommandReport(self.status, self.reason)


# https://mypy.readthedocs.io/en/stable/generics.html#declaring-decorators
def command(func: Callable[P, T]) -> Callable[P, T]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        with session_factory() as session:
            dfacto_model = args[0]
            dfacto_model.session = session  # type: ignore[attr-defined]
            return func(*args, **kwargs)

    return wrapper
