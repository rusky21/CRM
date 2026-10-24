import asyncio
import logging
from typing import Optional, Callable, Awaitable, Dict, Any, Tuple, List, Union, BinaryIO
from uuid import UUID

from telethon import TelegramClient, events
from telethon.tl import types, functions
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PasswordHashInvalidError,
    FloodWaitError,
    AuthKeyUnregisteredError,
)
from telethon.sessions import StringSession
from telethon.tl.types import User

from backend.app.models.account import AccountStatus
from backend.app.services.mtproto.fingerprint import DeviceFingerprint

logger = logging.getLogger(__name__)

# Callback type definitions
MessageHandlerCallback = Callable[[UUID, events.NewMessage.Event], Awaitable[None]]
MessageEditedCallback = Callable[[UUID, events.MessageEdited.Event], Awaitable[None]]
MessageDeletedCallback = Callable[[UUID, List[int], Optional[int]], Awaitable[None]]
UserTypingCallback = Callable[[UUID, int, str], Awaitable[None]]


class TelethonClientInstance:
    """
    Manages the lifecycle of a single Telethon MTProto client instance,
    including proxy routing, device fingerprinting, interactive authorization,
    outbound actions (typing, send_file, edit, delete), and full two-way update listening.
    """

    def __init__(
        self,
        account_id: UUID,
        phone: str,
        api_id: int,
        api_hash: str,
        fingerprint: DeviceFingerprint,
        session_string: Optional[str] = None,
        proxy_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.account_id = account_id
        self.phone = phone
        self.api_id = api_id
        self.api_hash = api_hash
        self.fingerprint = fingerprint
        self.proxy_config = proxy_config

        self.status: AccountStatus = AccountStatus.NEEDS_AUTH
        self.last_flood_wait: int = 0
        self._message_handler: Optional[MessageHandlerCallback] = None
        self._edit_handler: Optional[MessageEditedCallback] = None
        self._delete_handler: Optional[MessageDeletedCallback] = None
        self._typing_handler: Optional[UserTypingCallback] = None
        self._phone_code_hash: Optional[str] = None

        # Initialize StringSession
        self._session = StringSession(session_string or "")

        # Instantiate Telethon client with randomized realistic fingerprint
        self.client = TelegramClient(
            session=self._session,
            api_id=self.api_id,
            api_hash=self.api_hash,
            proxy=self.proxy_config,
            device_model=self.fingerprint.device_model,
            system_version=self.fingerprint.system_version,
            app_version=self.fingerprint.app_version,
            lang_code=self.fingerprint.lang_code,
            system_lang_code=self.fingerprint.system_lang_code,
            flood_sleep_threshold=60,
            auto_reconnect=True,
            retry_delay=2,
            connection_retries=5,
        )

    @property
    def is_connected(self) -> bool:
        return self.client.is_connected()

    async def connect(self) -> bool:
        """Connects the client to the Telegram MTProto cloud."""
        self.status = AccountStatus.CONNECTING
        try:
            await self.client.connect()
            if await self.client.is_user_authorized():
                self.status = AccountStatus.ACTIVE
                self._register_internal_listeners()
                logger.info(f"Account {self.account_id} ({self.phone}) connected and authorized.")
                return True
            else:
                self.status = AccountStatus.NEEDS_AUTH
                logger.warning(f"Account {self.account_id} ({self.phone}) connected but not authorized.")
                return False
        except FloodWaitError as exc:
            self.status = AccountStatus.FLOOD_WAIT
            self.last_flood_wait = exc.seconds
            logger.error(f"Account {self.account_id} hit FloodWait of {exc.seconds}s on connect.")
            return False
        except AuthKeyUnregisteredError:
            self.status = AccountStatus.BANNED
            logger.error(f"Account {self.account_id} session has been revoked/banned by Telegram.")
            return False
        except Exception as exc:
            self.status = AccountStatus.OFFLINE
            logger.error(f"Failed to connect account {self.account_id}: {exc}", exc_info=True)
            return False

    async def disconnect(self) -> None:
        """Disconnects the client cleanly from MTProto."""
        try:
            if self.client.is_connected():
                await self.client.disconnect()
            self.status = AccountStatus.OFFLINE
            logger.info(f"Account {self.account_id} ({self.phone}) disconnected.")
        except Exception as exc:
            logger.warning(f"Error during disconnect of account {self.account_id}: {exc}")

    async def is_authorized(self) -> bool:
        if not self.client.is_connected():
            return False
        return await self.client.is_user_authorized()

    async def get_me(self) -> Optional[User]:
        if not await self.is_authorized():
            return None
        return await self.client.get_me()

    def export_session_string(self) -> str:
        return self._session.save()

    # --- Outbound MTProto Actions (Real Client Parity) ---

    async def send_typing(self, peer_id: int) -> None:
        """Dispatches real 'typing' chat action to Telegram cloud."""
        if not self.client.is_connected():
            return
        try:
            async with self.client.action(peer_id, 'typing'):
                await asyncio.sleep(0.5)
        except Exception as exc:
            logger.warning(f"Could not send typing action to peer {peer_id}: {exc}")

    async def edit_message(self, peer_id: int, message_id: int, new_text: str) -> Any:
        """Edits an existing cloud message on Telegram servers."""
        if not self.client.is_connected():
            raise ConnectionError("Client is not connected to MTProto.")
        return await self.client.edit_message(entity=peer_id, message=message_id, text=new_text)

    async def delete_messages(self, peer_id: int, message_ids: List[int], revoke: bool = True) -> Any:
        """Deletes messages from Telegram cloud, revoking for both parties."""
        if not self.client.is_connected():
            raise ConnectionError("Client is not connected to MTProto.")
        return await self.client.delete_messages(entity=peer_id, message_ids=message_ids, revoke=revoke)

    async def send_file(
        self,
        peer_id: int,
        file: Union[str, bytes, BinaryIO],
        caption: Optional[str] = None,
        attributes: Optional[list] = None,
    ) -> Any:
        """Uploads and dispatches photo, document or voice note to peer."""
        if not self.client.is_connected():
            raise ConnectionError("Client is not connected to MTProto.")
        return await self.client.send_file(
            entity=peer_id,
            file=file,
            caption=caption,
            attributes=attributes,
        )

    # --- MTProto Profile Studio Methods ---

    async def update_profile(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        about: Optional[str] = None,
    ) -> Any:
        """Updates user's first name, last name, and about bio on Telegram cloud."""
        if not self.client.is_connected():
            raise ConnectionError("Client is not connected to MTProto.")
        kwargs: Dict[str, Any] = {}
        if first_name is not None:
            kwargs["first_name"] = first_name
        if last_name is not None:
            kwargs["last_name"] = last_name
        if about is not None:
            kwargs["about"] = about
        return await self.client(functions.account.UpdateProfileRequest(**kwargs))

    async def update_username(self, username: str) -> Any:
        """Updates user's public @username on Telegram cloud."""
        if not self.client.is_connected():
            raise ConnectionError("Client is not connected to MTProto.")
        clean_username = username.lstrip("@").strip()
        return await self.client(functions.account.UpdateUsernameRequest(username=clean_username))

    async def upload_profile_photo(self, photo: Union[str, bytes, BinaryIO]) -> Any:
        """Uploads and updates account profile photo on Telegram cloud."""
        if not self.client.is_connected():
            raise ConnectionError("Client is not connected to MTProto.")
        file_handle = await self.client.upload_file(photo)
        return await self.client(
            functions.photos.UploadProfilePhotoRequest(fallback=False, file=file_handle)
        )

    async def terminate_other_sessions(self) -> bool:
        """Terminates all other active Telegram sessions except this one."""
        if not self.client.is_connected():
            raise ConnectionError("Client is not connected to MTProto.")
        res = await self.client(functions.auth.ResetAuthorizationsRequest())
        return bool(res)

    # --- Interactive Login Workflow ---

    async def send_login_code(self) -> str:
        if not self.client.is_connected():
            await self.client.connect()

        try:
            sent_code = await self.client.send_code_request(self.phone)
            self._phone_code_hash = sent_code.phone_code_hash
            logger.info(f"Login code dispatched for account {self.account_id} ({self.phone}).")
            return self._phone_code_hash
        except FloodWaitError as exc:
            self.status = AccountStatus.FLOOD_WAIT
            self.last_flood_wait = exc.seconds
            raise

    async def complete_login_with_code(
        self,
        code: str,
        phone_code_hash: Optional[str] = None,
    ) -> Tuple[bool, bool, Optional[str]]:
        hash_to_use = phone_code_hash or self._phone_code_hash
        if not hash_to_use:
            raise ValueError("phone_code_hash is required to complete code verification.")

        try:
            await self.client.sign_in(phone=self.phone, code=code, phone_code_hash=hash_to_use)
            self.status = AccountStatus.ACTIVE
            self._register_internal_listeners()
            exported_session = self.export_session_string()
            logger.info(f"Account {self.account_id} ({self.phone}) authenticated successfully via code.")
            return True, False, exported_session

        except SessionPasswordNeededError:
            logger.info(f"Account {self.account_id} requires 2FA Cloud Password.")
            return False, True, None

        except (PhoneCodeInvalidError, PhoneCodeExpiredError) as exc:
            logger.warning(f"Invalid/expired code for account {self.account_id}: {exc}")
            raise

    async def complete_login_with_password(self, password: str) -> str:
        try:
            await self.client.sign_in(password=password)
            self.status = AccountStatus.ACTIVE
            self._register_internal_listeners()
            exported_session = self.export_session_string()
            logger.info(f"Account {self.account_id} ({self.phone}) authenticated successfully via 2FA.")
            return exported_session
        except PasswordHashInvalidError as exc:
            logger.warning(f"Invalid 2FA password provided for account {self.account_id}.")
            raise exc

    # --- Handlers & Internal Listeners Registration ---

    def set_message_handler(self, handler: MessageHandlerCallback) -> None:
        self._message_handler = handler

    def set_edit_handler(self, handler: MessageEditedCallback) -> None:
        self._edit_handler = handler

    def set_delete_handler(self, handler: MessageDeletedCallback) -> None:
        self._delete_handler = handler

    def set_typing_handler(self, handler: UserTypingCallback) -> None:
        self._typing_handler = handler

    def _register_internal_listeners(self) -> None:
        """Binds incoming message, edit, delete, and typing MTProto events."""

        # 1. Inbound New Messages
        @self.client.on(events.NewMessage(incoming=True))
        async def _on_new_message(event: events.NewMessage.Event) -> None:
            if self._message_handler:
                try:
                    await self._message_handler(self.account_id, event)
                except Exception as exc:
                    logger.error(f"Error in message handler for {self.account_id}: {exc}", exc_info=True)

        # 2. Inbound Message Edited
        @self.client.on(events.MessageEdited)
        async def _on_message_edited(event: events.MessageEdited.Event) -> None:
            if self._edit_handler:
                try:
                    await self._edit_handler(self.account_id, event)
                except Exception as exc:
                    logger.error(f"Error in edit handler for {self.account_id}: {exc}", exc_info=True)

        # 3. Message Deleted
        @self.client.on(events.MessageDeleted)
        async def _on_message_deleted(event: events.MessageDeleted.Event) -> None:
            if self._delete_handler:
                try:
                    await self._delete_handler(self.account_id, event.deleted_ids, event.chat_id)
                except Exception as exc:
                    logger.error(f"Error in delete handler for {self.account_id}: {exc}", exc_info=True)

        # 4. Inbound User Typing Status
        @self.client.on(events.Raw(types.UpdateUserTyping))
        async def _on_user_typing(event: types.UpdateUserTyping) -> None:
            if self._typing_handler:
                try:
                    action_type = "typing"
                    if isinstance(event.action, types.SendMessageUploadPhotoAction):
                        action_type = "upload_photo"
                    elif isinstance(event.action, types.SendMessageRecordAudioAction):
                        action_type = "record_audio"
                    await self._typing_handler(self.account_id, event.user_id, action_type)
                except Exception as exc:
                    logger.debug(f"Error in typing handler for {self.account_id}: {exc}")
