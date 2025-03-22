"""Provides an asynchronous API client for interacting with MHI HVAC systems.

This module defines the MHIHVACLocalAPI class, which handles communication
with the local API of MHI HVAC systems. It supports login, fetching data,
and sending commands, including automatic re-authentication and retry
mechanisms for handling session expirations.
"""

import asyncio
from collections.abc import Awaitable, Callable
import json
import logging
from typing import Any, TypeVar, cast

import aiohttp

from .utils import format_exception

_LOGGER = logging.getLogger(__name__)

HTTP_HEADERS: dict[str, str] = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "User-Agent": "pymhihvac",
}


class LoginFailedException(Exception):
    """Raised when login to MHI HVAC system fails."""


class NoSessionCookieException(Exception):
    """Raised when login to MHI HVAC system does not return session cookie."""


class ApiCallFailedException(Exception):
    """Raised when sending command to MHI HVAC system fails."""


class SessionExpiredException(Exception):
    """Raised when the session cookie is expired or invalid."""


class SessionNotInitializedException(Exception):
    """Raised when the session cookie is expired or invalid."""


T = TypeVar("T")


def reauth_retry(
    max_retries: int = 3,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Handle re-authentication and retries for session expiry."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(self: "MHIHVACLocalAPI", *args: Any, **kwargs: Any) -> T:
            for attempt in range(max_retries + 1):
                try:
                    return await func(self, *args, **kwargs)
                except SessionExpiredException as e:
                    if attempt < max_retries:
                        _LOGGER.debug(
                            "Session expired, re-authenticating (attempt %d/%d)",
                            attempt + 1,
                            max_retries,
                        )
                        self._session_cookie = await self._async_login()
                    else:
                        raise ApiCallFailedException(
                            f"Max re-authentication attempts ({max_retries}) reached."
                        ) from e
            raise ApiCallFailedException(
                f"Max re-authentication attempts ({max_retries}) reached."
            )

        return wrapper

    return decorator


class MHIHVACLocalAPI:
    """Class to interact with the MHI HVAC local API."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client.

        Args:
            host: The HVAC system host or IP address.
            username: The username to use for login.
            password: The password to use for login.
            session: Optional aiohttp ClientSession to use for requests.
                     If None, a new session will be created internally.

        """
        self._username: str = username
        self._password: str = password
        self._api_login_url: str = f"http://{host}/login.asp"
        self._api_url: str = f"http://{host}/json/group_list_json.asp"
        self._session: aiohttp.ClientSession | None = session
        self._session_cookie: str | None = None

        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._session_created_internally: bool = (
                True  # Set flag if session was created here
            )
        else:
            self._session_created_internally = (
                False  # Flag session was provided externally
            )

    @property
    def session_cookie(self) -> str | None:
        """Return the cookie of the session."""
        return self._session_cookie

    async def close_session(self) -> None:
        """Close the aiohttp session if it was created internally."""
        if self._session and self._session_created_internally:
            _LOGGER.debug("Closing session")
            await self._session.close()
            self._session = None
            _LOGGER.debug("Session closed")

    @reauth_retry()
    async def async_get_raw_data(self) -> dict[str, Any]:
        """Fetch data from HVAC system with error handling."""
        if not self._session:
            raise SessionNotInitializedException("Session is not initialized")
        if not self._session_cookie:
            self._session_cookie = await self.async_login()
        headers: dict[str, str] = HTTP_HEADERS.copy()
        headers["Cookie"] = self._session_cookie
        payload: str = '={"GetReqGroupData":{"FloorNo":["1"]}}'
        try:
            async with asyncio.timeout(10):
                async with self._session.post(
                    self._api_url, data=payload, headers=headers
                ) as resp:
                    resp_text: str = await resp.text()
                    data: dict[str, Any] = json.loads(resp_text)
                    floor_data: dict[str, Any] = data.get("GetResGroupData", {}).get(
                        "FloorData", [{}]
                    )[0]
                    if floor_data.get("FloorNo") == "-1":
                        raise SessionExpiredException
                    # Cast the value to dict[str, Any] so that mypy accepts it.
                    return cast(dict[str, Any], floor_data.get("GroupData", {}))
        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError) as e:
            _LOGGER.error("Error fetching data: %s", format_exception(e))
            raise

    async def async_set_group_property(
        self, group_no: str, properties: dict[str, Any]
    ) -> dict[str, Any]:
        """Wrap the given payload by adding the GroupNo inside SetReqChangeGroup."""
        payload: dict[str, Any] = properties.copy()
        payload.setdefault("GroupNo", group_no)
        payload = {"SetReqChangeGroup": payload}
        return await self._async_send_command(payload)

    async def async_set_all_property(
        self, properties: dict[str, Any]
    ) -> dict[str, Any]:
        """Wrap the given payload with the SetReqChangeAll key."""
        payload: dict[str, Any] = {"SetReqChangeAll": properties.copy()}
        return await self._async_send_command(payload)

    @reauth_retry()
    async def _async_send_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a command to the API asynchronously with limited re-authentication attempts."""
        if not self._session:
            raise SessionNotInitializedException("Session is not initialized")
        if not isinstance(payload, dict):
            _LOGGER.debug("Payload '%s' is not a dictionary", payload)
            return {"_async_send_command": "Payload is not a dictionary"}
        headers: dict[str, str] = HTTP_HEADERS.copy()
        data: str = f"={json.dumps(payload)}"
        if self._session_cookie:
            headers["Cookie"] = self._session_cookie
        try:
            async with asyncio.timeout(10):
                _LOGGER.debug("Sending command: %s", data)
                async with self._session.post(
                    self._api_url,
                    data=data,
                    headers=headers,
                ) as resp:
                    resp_text: str = await resp.text()
                    if resp.status != 200:
                        raise ApiCallFailedException(
                            f"Command failed with HTTP {resp.status}."
                        )
                    if not resp_text.strip():
                        raise SessionExpiredException
                    # Cast the result of json.loads to dict[str, Any]
                    return cast(dict[str, Any], json.loads(resp_text))
                return resp_text
        except (aiohttp.ClientError, TimeoutError) as e:
            _LOGGER.error("Command failed with error: %s", format_exception(e))
            raise

    async def async_login(self) -> str:
        """Login to the HVAC system and return the session cookie.

        Performs a login via the HVAC's /login.asp endpoint using the provided
        credentials. Returns the session cookie if successful.

        Returns:
            A string containing the session cookie.

        Raises:
            Exception: If login fails or no cookie is returned.

        """
        return await self._async_login()

    async def _async_login(self) -> str:
        """Login to the HVAC system and return the session cookie.

        Internal method to perform the login.
        """
        if not self._session:
            raise SessionNotInitializedException("Session is not initialized")
        headers: dict[str, str] = HTTP_HEADERS.copy()
        data: dict[str, str] = {"Id": self._username, "Password": self._password}
        try:
            async with (
                asyncio.timeout(10),
                self._session.post(
                    self._api_login_url,
                    data=data,
                    headers=headers,
                    allow_redirects=False,
                ) as resp,
            ):
                if resp.status != 302:
                    raise LoginFailedException(
                        f"Login failed with status {resp.status}"
                    )
                cookie: str | None = resp.headers.get("Set-Cookie")
                if not cookie:
                    raise NoSessionCookieException(
                        "Login did not return a session cookie"
                    )
                _LOGGER.debug("Logged in, session cookie: %s", cookie)
                return cookie
        except (aiohttp.ClientError, TimeoutError) as e:
            _LOGGER.error("Login error: %s", format_exception(e))
            raise
