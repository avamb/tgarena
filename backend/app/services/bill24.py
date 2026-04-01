"""
Bill24/TixGear API Client

Implements async HTTP client for all Bill24 API commands.
Reference: Документация API BL24 для билетных агентов.md
"""

import logging
from typing import Any, Dict, List, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class Bill24Error(Exception):
    """Base exception for Bill24 API errors."""

    def __init__(self, code: int, message: str, cause: Optional[str] = None):
        self.code = code
        self.message = message
        self.cause = cause
        super().__init__(f"Bill24 Error {code}: {message}")


class Bill24SessionError(Bill24Error):
    """Session-related error (invalid userId/sessionId)."""

    pass


class Bill24Client:
    """
    Async client for Bill24/TixGear API.

    All requests use HTTPS POST with JSON body.
    See protocol documentation for command details.
    """

    def __init__(
        self,
        fid: int,
        token: str,
        zone: str = "test",
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ):
        """
        Initialize Bill24 client.

        Args:
            fid: Frontend ID (Bill24 agent ID)
            token: API token for authentication
            zone: 'test' or 'real'
            user_id: Bill24 user ID for session commands
            session_id: Bill24 session ID for session commands
        """
        self.fid = fid
        self.token = token
        self.zone = zone
        self.user_id = user_id
        self.session_id = session_id

        # Select API URL based on zone
        self.base_url = (
            settings.BILL24_TEST_URL if zone == "test" else settings.BILL24_REAL_URL
        )

        # HTTP client with compression support
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                },
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_request(
        self, command: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build request payload with required fields."""
        request = {
            "command": command,
            "fid": self.fid,
            "token": self.token,
            "locale": "ru-RU",
        }

        # Add session info for session commands
        if self.user_id and self.session_id:
            request["userId"] = self.user_id
            request["sessionId"] = self.session_id

        # Add command-specific parameters
        if params:
            request.update(params)

        return request

    def _handle_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process response and handle errors."""
        result_code = response.get("resultCode", -1)

        if result_code == 0:
            return response

        description = response.get("description", "Unknown error")
        cause = response.get("cause")

        if result_code == 1:
            # Session error
            raise Bill24SessionError(result_code, description, cause)

        raise Bill24Error(result_code, description, cause)

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def _request(
        self, command: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make API request with retry logic.

        Args:
            command: Bill24 command name
            params: Additional parameters

        Returns:
            Response data

        Raises:
            Bill24Error: On API error
            Bill24SessionError: On session error
        """
        client = await self._get_client()
        request_body = self._build_request(command, params)

        logger.debug(f"Bill24 Request: {command}", extra={"params": params})

        try:
            response = await client.post(self.base_url, json=request_body)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Bill24 HTTP Error: {e.response.status_code}")
            raise Bill24Error(-1, f"HTTP Error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Bill24 Request Failed: {e}")
            raise

        logger.debug(f"Bill24 Response: {command}", extra={"code": data.get("resultCode")})

        return self._handle_response(data)

    # =========================================================================
    # Public API Commands (No Session Required)
    # =========================================================================

    async def get_countries(self) -> List[Dict[str, Any]]:
        """Get list of countries with events."""
        response = await self._request("GET_COUNTRIES")
        return response.get("countryList", [])

    async def get_cities(self, country_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of cities."""
        params = {}
        if country_id:
            params["countryId"] = country_id
        response = await self._request("GET_CITIES", params)
        return response.get("cityList", [])

    async def get_venues(
        self, city_id: Optional[int] = None, venue_type_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get list of venues (places)."""
        params = {}
        if city_id:
            params["cityId"] = city_id
        if venue_type_id:
            params["venueTypeId"] = venue_type_id
        response = await self._request("GET_VENUES", params)
        return response.get("venueList", [])

    async def get_all_actions(self) -> Dict[str, Any]:
        """
        Get all events with full details.

        Returns complete event data for local caching.
        The response contains: countryList, cityList, kindList, genreList, actionList.
        Each event in actionList has: actionId, fullActionName, firstEventDate (dd.MM.yyyy),
        lastEventDate, minPrice, maxPrice, actionEventList, etc.
        Note: There is no 'actionDate' field — use 'firstEventDate' instead.
        """
        response = await self._request("GET_ALL_ACTIONS")

        # Debug: log response structure for diagnostics
        action_list = response.get("actionList", [])
        logger.info(
            f"GET_ALL_ACTIONS: resultCode={response.get('resultCode')}, "
            f"events_count={len(action_list)}, "
            f"response_keys={list(response.keys())}"
        )
        if action_list:
            sample = action_list[0]
            logger.debug(
                f"GET_ALL_ACTIONS sample event: actionId={sample.get('actionId')}, "
                f"name={sample.get('fullActionName')}, "
                f"firstEventDate={sample.get('firstEventDate')}, "
                f"event_keys={list(sample.keys())}"
            )

        return response

    async def get_actions_v2(
        self,
        city_id: Optional[int] = None,
        venue_id: Optional[int] = None,
        genre_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of events with optional filters."""
        params = {}
        if city_id:
            params["cityId"] = city_id
        if venue_id:
            params["venueId"] = venue_id
        if genre_id:
            params["genreId"] = genre_id
        response = await self._request("GET_ACTIONS_V2", params)
        return response.get("actionList", [])

    async def get_action_ext(self, action_id: int) -> Dict[str, Any]:
        """Get detailed information about specific event."""
        params = {"actionId": action_id}
        response = await self._request("GET_ACTION_EXT", params)
        return response

    async def get_seat_list(self, action_event_id: int) -> List[Dict[str, Any]]:
        """
        Get seat availability for specific event session.

        Args:
            action_event_id: ID of specific event session (not action!)

        Returns:
            List of seat objects with status and price
        """
        params = {"actionEventId": action_event_id}
        response = await self._request("GET_SEAT_LIST", params)
        return response.get("seatList", [])

    # =========================================================================
    # Session Commands (Require userId/sessionId)
    # =========================================================================

    async def create_user(
        self,
        telegram_chat_id: int,
        first_name: str,
        last_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create new user in Bill24 system.

        Args:
            telegram_chat_id: Telegram chat ID (used as identifier)
            first_name: User's first name
            last_name: User's last name

        Returns:
            Dict with userId and sessionId
        """
        params = {
            "telegramChatId": str(telegram_chat_id),
            "firstName": first_name,
        }
        if last_name:
            params["lastName"] = last_name

        response = await self._request("CREATE_USER", params)
        return {
            "userId": response.get("userId"),
            "sessionId": response.get("sessionId"),
        }

    async def reserve_seats(
        self,
        action_event_id: int,
        seat_ids: List[int],
    ) -> Dict[str, Any]:
        """
        Reserve seats for user.

        Args:
            action_event_id: Event session ID
            seat_ids: List of seat IDs to reserve

        Returns:
            Dict with reserved seats and cart timeout
        """
        params = {
            "actionEventId": action_event_id,
            "seatList": seat_ids,
            "type": "RESERVE",
        }
        response = await self._request("RESERVATION", params)
        return {
            "seatList": response.get("seatList", []),
            "cartTimeout": response.get("cartTimeout", 600),
            "totalSum": response.get("totalSum", 0),
        }

    async def unreserve_seats(
        self,
        action_event_id: int,
        seat_ids: List[int],
    ) -> Dict[str, Any]:
        """Remove seats from reservation."""
        params = {
            "actionEventId": action_event_id,
            "seatList": seat_ids,
            "type": "UN_RESERVE",
        }
        return await self._request("RESERVATION", params)

    async def unreserve_all(self, action_event_id: int) -> Dict[str, Any]:
        """Remove all seats from reservation."""
        params = {
            "actionEventId": action_event_id,
            "type": "UN_RESERVE_ALL",
        }
        return await self._request("RESERVATION", params)

    async def get_cart(self) -> Dict[str, Any]:
        """Get current cart contents."""
        response = await self._request("GET_CART")
        return response

    async def create_order(
        self,
        success_url: str,
        fail_url: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create order from current cart.

        Args:
            success_url: URL for redirect after successful payment (required)
            fail_url: URL for redirect after failed payment (required)
            email: Customer email (optional, using Telegram)
            phone: Customer phone (optional)
            full_name: Customer full name for ticket (optional)

        Returns:
            Dict with orderId, formUrl (payment link), and status
        """
        params = {
            "successUrl": success_url,
            "failUrl": fail_url,
        }
        if email:
            params["email"] = email
        if phone:
            params["phone"] = phone
        if full_name:
            params["fullName"] = full_name

        response = await self._request("CREATE_ORDER", params)
        return {
            "orderId": response.get("orderId"),
            "formUrl": response.get("formUrl"),
            "externalOrderId": response.get("externalOrderId"),
            "statusExtStr": response.get("statusExtStr"),
            "statusExtInt": response.get("statusExtInt"),
        }

    async def pay_order(self, order_id: int) -> Dict[str, Any]:
        """
        Mark order as paid.

        Used when payment is processed externally.
        """
        params = {"orderId": order_id}
        response = await self._request("PAY_ORDER", params)
        return response

    async def cancel_order(self, order_id: int) -> Dict[str, Any]:
        """Cancel unpaid order."""
        params = {"orderId": order_id}
        response = await self._request("CANCEL_ORDER", params)
        return response

    async def get_order_info(self, order_id: int) -> Dict[str, Any]:
        """Get order status and details."""
        params = {"orderId": order_id}
        response = await self._request("GET_ORDER_INFO", params)
        return response

    async def get_tickets_by_order(self, order_id: int) -> List[Dict[str, Any]]:
        """
        Get tickets for paid order.

        Returns ticket data including QR codes and barcodes.
        """
        params = {"orderId": order_id}
        response = await self._request("GET_TICKETS_BY_ORDER", params)
        return response.get("ticketList", [])

    async def print_tickets(self, order_id: int) -> bytes:
        """
        Get PDF tickets for order.

        Returns raw PDF bytes.
        """
        params = {"orderId": order_id}
        response = await self._request("PRINT_TICKETS", params)
        # PDF data is base64 encoded in response
        import base64

        pdf_data = response.get("pdfData", "")
        return base64.b64decode(pdf_data)


# Factory function for creating configured clients
async def get_bill24_client(
    agent_fid: int,
    agent_token: str,
    zone: str = "test",
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> Bill24Client:
    """Create configured Bill24 client for specific agent."""
    return Bill24Client(
        fid=agent_fid,
        token=agent_token,
        zone=zone,
        user_id=user_id,
        session_id=session_id,
    )
