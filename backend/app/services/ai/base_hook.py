import abc
import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class BaseAIAutoReplyHook(abc.ABC):
    """
    Abstract interface for AI auto-reply and outbound message transformation hooks.
    Can be extended to inject LLM responses, sentiment detection, or brand tone corrections.
    """

    @abc.abstractmethod
    async def should_intercept(
        self,
        account_id: UUID,
        peer_id: int,
        message_text: str,
    ) -> bool:
        """Determines if the outbound message should be processed or modified by AI."""
        pass

    @abc.abstractmethod
    async def process_outbound(
        self,
        account_id: UUID,
        peer_id: int,
        message_text: str,
    ) -> str:
        """Processes and optionally transforms the outbound message text prior to MTProto dispatch."""
        pass


class PassThroughAIHook(BaseAIAutoReplyHook):
    """Default pass-through implementation: leaves outbound text untouched."""

    async def should_intercept(
        self,
        account_id: UUID,
        peer_id: int,
        message_text: str,
    ) -> bool:
        return False

    async def process_outbound(
        self,
        account_id: UUID,
        peer_id: int,
        message_text: str,
    ) -> str:
        return message_text
