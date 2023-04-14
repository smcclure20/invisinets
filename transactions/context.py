import uuid
import logging
from typing import Any, Optional
from transactions.actions import *
from abc import ABC, abstractmethod
from collections import OrderedDict

logger = logging.getLogger(__name__)


class Context(ABC):
    @abstractmethod
    def add_action(self, action: Action):
        return NotImplemented

    @abstractmethod
    def commit(self):
        return NotImplemented

    @abstractmethod
    def rollback(self):
        return NotImplemented


class MultiActionContext(Context):

    actions: OrderedDict[uuid.UUID, Action] = OrderedDict()
    exec_stack: OrderedDict[uuid.UUID, (Action, Any)] = OrderedDict()

    def add_action(self, action: Action) -> uuid.UUID:
        action_id = uuid.uuid4()
        self.actions[action_id] = action
        return action_id

    def commit(self) -> Optional[dict[uuid.UUID, Any]]:
        self.exec_stack.clear()
        for action_id, action in self.actions.items():
            try:
                result = action.f()
                self.exec_stack[action_id] = (action, result)
            except Exception as e:
                logging.error(f"Failed to execute one of the actions: {e}")
                logging.error(f"Rolling back previous executions, "
                              f"current execution stack: {self.exec_stack.values()}")
                self.rollback()
                return None

        self.actions.clear()
        return {action_id: result for action_id, (_, result) in self.exec_stack.items()}

    def rollback(self):
        for action_id, (action, result) in reversed(self.exec_stack.items()):
            try:
                action.undo(result)
            except Exception as e:
                logger.error(f"Failed to undo action: {e}")

        self.exec_stack.clear()


class SingleActionContext(Context):
    def add_action(self, action: Action) -> Any:
        """
        Single action context calls the underlying operation inplace, and
        does not trigger rollback if it fails.
        """
        return action.f()

    def commit(self):
        raise NotImplementedError("Single-action context does not "
                                  "implement either commit or rollback. "
                                  "Call begin() first to start a multi-action context")

    def rollback(self):
        raise NotImplementedError("Single-action context does not "
                                  "implement either commit or rollback. "
                                  "Call begin() first to start a multi-action context")


current = SingleActionContext()


def begin() -> None:
    global current
    current = MultiActionContext()


def commit() -> Optional[dict[uuid.UUID, Any]]:
    global current
    results = current.commit()
    current = SingleActionContext()
    return results
