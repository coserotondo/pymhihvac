# test_api.py
import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from .api import (  # Replace with actual module name
    ApiCallFailedException,
    LoginFailedException,
    MHIHVACLocalAPI,
    NoSessionCookieException,
    SessionExpiredException,
    reauth_retry,
)


@pytest.fixture
async def mock_session():
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.__aenter__ = AsyncMock()
    session.__aexit__ = AsyncMock()
    return session


@pytest.fixture
def api_client(mock_session):
    return MHIHVACLocalAPI(
        host="testhost",
        username="testuser",
        password="testpass",
        session=mock_session,
    )


@pytest.mark.asyncio
async def test_successful_login(api_client, mock_session):
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.status = 302
    mock_response.headers = {"Set-Cookie": "session=123"}

    # Setup async context manager
    mock_post = AsyncMock()
    mock_post.__aenter__.return_value = mock_response
    mock_session.post.return_value = mock_post

    # Execute
    cookie = await api_client.async_login()
    assert cookie == "session=123"

    # Verify
    assert cookie == "session=123"
    mock_session.post.assert_called_once_with(
        "http://testhost/login.asp",
        data={"Id": "testuser", "Password": "testpass"},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "pymhihvac",
        },
        allow_redirects=False,
    )


@pytest.mark.asyncio
async def test_login_failure_status_code(api_client, mock_session):
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_session.post.return_value = mock_response

    with pytest.raises(LoginFailedException):
        await api_client.async_login()


@pytest.mark.asyncio
async def test_login_missing_cookie(api_client, mock_session):
    mock_response = AsyncMock()
    mock_response.status = 302
    mock_response.headers = {}

    # Add async context manager setup
    mock_post = AsyncMock()
    mock_post.__aenter__.return_value = mock_response
    mock_session.post.return_value = mock_post

    with pytest.raises(NoSessionCookieException):
        await api_client.async_login()


@pytest.mark.asyncio
async def test_get_raw_data_success(api_client, mock_session):
    # Setup mocks
    api_client._session_cookie = "valid_cookie"
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(
        return_value=json.dumps(
            {
                "GetResGroupData": {
                    "FloorData": [{"FloorNo": "1", "GroupData": {"test": "data"}}]
                }
            }
        )
    )
    # Setup async context manager
    mock_post = AsyncMock()
    mock_post.__aenter__.return_value = mock_response
    mock_session.post.return_value = mock_post

    # Execute
    result = await api_client.async_get_raw_data()
    assert result == {"test": "data"}

    # Verify
    assert result == {"test": "data"}
    mock_session.post.assert_called_once_with(
        "http://testhost/json/data_json.asp",
        data='={"GetReqGroupData":{"FloorNo":["1"]}}',
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "pymhihvac",
            "Cookie": "valid_cookie",
        },
    )


@pytest.mark.asyncio
async def test_get_raw_data_session_expiry(api_client, mock_session):
    # Setup expired session scenario
    api_client._session_cookie = "expired_cookie"
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(
        return_value=json.dumps({"GetResGroupData": {"FloorData": [{"FloorNo": "-1"}]}})
    )
    # Add async context manager setup
    mock_post = AsyncMock()
    mock_post.__aenter__.return_value = mock_response
    mock_session.post.return_value = mock_post

    with patch.object(api_client, "async_login", AsyncMock()) as mock_login:
        with pytest.raises(ApiCallFailedException):
            await api_client.async_get_raw_data()
        assert mock_login.call_count == 3


@pytest.mark.asyncio
async def test_send_command_success(api_client, mock_session):
    api_client._session_cookie = "valid_cookie"
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value='{"success": true}')  # Fix extra quote

    mock_post = AsyncMock()
    mock_post.__aenter__.return_value = mock_response
    mock_session.post.return_value = mock_post

    result = await api_client._async_send_command({"test": "payload"})
    assert result == '{"success": true}'  # Remove extra quote


@pytest.mark.asyncio
async def test_send_command_expired_session(api_client, mock_session):
    api_client._session_cookie = "expired_cookie"
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="")
    mock_session.post.return_value = mock_response

    with pytest.raises(ApiCallFailedException):
        await api_client._async_send_command({"test": "payload"})


@pytest.mark.asyncio
async def test_send_command_http_error(api_client, mock_session):
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_session.post.return_value = mock_response

    with pytest.raises(ApiCallFailedException):
        await api_client._async_send_command({"test": "payload"})


@pytest.mark.asyncio
async def test_reauth_retry_decorator(api_client):
    mock_func = AsyncMock(side_effect=SessionExpiredException())
    decorated_func = reauth_retry(max_retries=2)(mock_func)  # Use direct import

    with (
        pytest.raises(ApiCallFailedException),
        patch.object(api_client, "async_login", AsyncMock()) as mock_login,
    ):
        await decorated_func(api_client)

    assert mock_func.call_count == 3  # 2 retries + initial attempt
    assert mock_login.call_count == 2


@pytest.mark.asyncio
async def test_session_management(api_client, mock_session):
    # Test internal session creation
    api = MHIHVACLocalAPI("testhost", "user", "pass")
    assert api._session_created_internally is True
    await api.close_session()
    assert api._session is None

    # Test external session handling
    external_session = AsyncMock()
    api = MHIHVACLocalAPI("testhost", "user", "pass", session=external_session)
    assert api._session_created_internally is False
    await api.close_session()
    external_session.close.assert_not_called()
