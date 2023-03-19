# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import enum
from typing import Any, NamedTuple, Optional

from dfacto.backend.db import session_factory


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


def command(func):
    def wrapper(self, *args, **kwargs):
        with session_factory() as session:
            self.session = session
            return func(self, *args, **kwargs)
    return wrapper
