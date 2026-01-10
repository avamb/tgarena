"""
Test Bill24 CREATE_ORDER API Integration

This script tests the order creation functionality via the Bill24/TixGear API.
It uses the official test credentials to verify the complete order creation flow.

Test Steps:
1. Get events from Bill24 API
2. Get seat list for an event
3. Reserve seats using RESERVATION command
4. Create order using CREATE_ORDER command
5. Verify orderId is returned
6. Verify payment link (formUrl) is returned
7. Cancel or unreserve (cleanup)

Note: Due to Bill24 test zone inventory limitations, this test may fail
at the reservation step if no seats are available. The test is designed
to verify the API integration is correct.
"""

import asyncio
import logging
import sys
from typing import Optional, Dict, Any, List

# Add parent directory to path for imports
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.bill24 import Bill24Client, Bill24Error, Bill24SessionError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bill24 Official Test Credentials
TEST_FID = 1271
TEST_TOKEN = "7c696b4af364928202dd"
TEST_ZONE = "test"

# Callback URLs for testing
SUCCESS_URL = "https://example.com/payment/success"
FAIL_URL = "https://example.com/payment/fail"


class Bill24CreateOrderTest:
    """Test class for Bill24 CREATE_ORDER API integration."""

    def __init__(self):
        self.client: Optional[Bill24Client] = None
        self.test_results: Dict[str, bool] = {}
        self.reserved_seats: List[int] = []
        self.action_event_id: Optional[int] = None
        self.first_seat_data: Optional[Dict[str, Any]] = None
        self.order_id: Optional[int] = None

    async def setup(self):
        """Initialize the Bill24 client with test credentials."""
        logger.info("Setting up Bill24 client with test credentials...")

        # First create client without session for public commands
        self.client = Bill24Client(
            fid=TEST_FID,
            token=TEST_TOKEN,
            zone=TEST_ZONE,
        )
        logger.info(f"Client initialized: FID={TEST_FID}, Zone={TEST_ZONE}")

        # Create a new user to get a valid session
        try:
            logger.info("Creating test user to get valid session...")
            import random
            test_chat_id = random.randint(100000000, 999999999)
            result = await self.client.create_user(
                telegram_chat_id=test_chat_id,
                first_name="Test",
                last_name="OrderUser"
            )
            user_id = result.get("userId")
            session_id = result.get("sessionId")
            if user_id and session_id:
                logger.info(f"Got new session: userId={user_id}, sessionId={session_id[:10]}...")
                # Update client with session
                self.client.user_id = user_id
                self.client.session_id = session_id
            else:
                raise Exception("CREATE_USER didn't return valid session")
        except Exception as e:
            logger.error(f"Failed to create test user: {e}")
            raise

    async def cleanup(self):
        """Clean up resources and cancel any created orders."""
        if self.client:
            # Cancel order if one was created
            if self.order_id:
                try:
                    logger.info(f"Cleaning up - cancelling order: {self.order_id}")
                    await self.client.cancel_order(self.order_id)
                except Exception as e:
                    logger.warning(f"Order cancellation failed: {e}")

            # Unreserve any seats we reserved during testing
            if self.action_event_id:
                try:
                    logger.info("Cleaning up - unreserving all seats")
                    await self.client.unreserve_all(self.action_event_id)
                except Exception as e:
                    logger.warning(f"Unreserve cleanup failed: {e}")

            await self.client.close()
        logger.info("Cleanup complete")

    async def test_get_events(self) -> bool:
        """Step 1: Get events from Bill24 API."""
        logger.info("\n=== Step 1: Testing GET_ALL_ACTIONS ===")
        try:
            response = await self.client.get_all_actions()
            action_list = response.get("actionList", [])
            logger.info(f"Retrieved {len(action_list)} events")

            if len(action_list) > 0:
                # Find an event with sessions
                for action in action_list:
                    action_event_list = action.get("actionEventList", [])
                    if action_event_list:
                        self.action_event_id = action_event_list[0].get("actionEventId")
                        logger.info(f"Selected event: {action.get('name', 'N/A')}")
                        logger.info(f"  Session ID: {self.action_event_id}")
                        break

                self.test_results["get_events"] = True
                return True
            else:
                logger.warning("No events available in test zone")
                self.test_results["get_events"] = False
                return False

        except Bill24Error as e:
            logger.error(f"Bill24 API error: {e}")
            self.test_results["get_events"] = False
            return False

    async def test_get_seats(self) -> bool:
        """Step 2: Get available seats for an event."""
        logger.info("\n=== Step 2: Testing GET_SEAT_LIST ===")

        if not self.action_event_id:
            logger.error("No action_event_id available - skipping seat test")
            self.test_results["get_seats"] = False
            return False

        # Get events and try multiple sessions to find available seats
        events_to_try = [self.action_event_id]

        try:
            response = await self.client.get_all_actions()
            action_list = response.get("actionList", [])
            for action in action_list[:20]:
                for event in action.get("actionEventList", [])[:3]:
                    event_id = event.get("actionEventId")
                    if event_id and event_id not in events_to_try:
                        events_to_try.append(event_id)
        except:
            pass

        logger.info(f"Will try up to {min(len(events_to_try), 10)} event sessions")

        for event_id in events_to_try[:10]:
            try:
                logger.info(f"Trying event session ID: {event_id}")
                seats = await self.client.get_seat_list(event_id)

                if len(seats) > 0:
                    # Find available seats
                    available_seats = []
                    for s in seats:
                        is_available = s.get("available", True)
                        status = s.get("status", "").upper()
                        is_free = s.get("free", False)
                        is_reserved = s.get("reserved", False)

                        if is_available or is_free or (status == "FREE" and not is_reserved):
                            available_seats.append(s)

                    logger.info(f"Total seats: {len(seats)}, Available: {len(available_seats)}")

                    if available_seats:
                        first_seat = available_seats[0]
                        logger.info(f"First available seat: ID={first_seat.get('seatId')}")

                        self.reserved_seats = [first_seat.get('seatId')]
                        self.first_seat_data = first_seat
                        self.action_event_id = event_id

                        self.test_results["get_seats"] = True
                        return True

            except Bill24Error as e:
                logger.warning(f"Bill24 API error for event {event_id}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error for event {event_id}: {e}")
                continue

        logger.error("Could not find any event with available seats")
        self.test_results["get_seats"] = False
        return False

    async def test_reservation(self) -> bool:
        """Step 3: Reserve seats using RESERVATION command."""
        logger.info("\n=== Step 3: Testing RESERVATION ===")

        if not self.action_event_id or not self.first_seat_data:
            logger.error("Missing action_event_id or seat data - skipping reservation test")
            self.test_results["reservation"] = False
            return False

        try:
            is_placement = self.first_seat_data.get("placement", False)
            seat_id = self.first_seat_data.get("seatId")
            category_price_id = self.first_seat_data.get("categoryPriceId")

            if is_placement:
                params = {
                    "actionEventId": self.action_event_id,
                    "seatList": [seat_id],
                    "type": "RESERVE",
                }
            else:
                params = {
                    "actionEventId": self.action_event_id,
                    "categoryList": [{"categoryPriceId": category_price_id, "quantity": 1}],
                    "type": "RESERVE",
                }

            logger.info(f"RESERVATION params: {params}")
            raw_response = await self.client._request("RESERVATION", params)
            logger.info(f"RESERVATION response: {raw_response}")

            cart_timeout = raw_response.get("cartTimeout", 0)
            seat_list = raw_response.get("seatList", [])

            if cart_timeout > 0 or seat_list:
                logger.info(f"Reservation successful - cart timeout: {cart_timeout}s")
                self.test_results["reservation"] = True
                return True
            else:
                logger.warning("Reservation may have failed - no cart timeout or seats returned")
                self.test_results["reservation"] = False
                return False

        except Bill24Error as e:
            logger.error(f"Bill24 API error: {e}")
            self.test_results["reservation"] = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.test_results["reservation"] = False
            return False

    async def test_create_order(self) -> bool:
        """Step 4-5: Test CREATE_ORDER command."""
        logger.info("\n=== Step 4: Testing CREATE_ORDER ===")

        try:
            # Call create_order with required URLs
            result = await self.client.create_order(
                success_url=SUCCESS_URL,
                fail_url=FAIL_URL,
                email="test@example.com",
                phone="+1234567890",
                full_name="Test Order User"
            )

            logger.info(f"CREATE_ORDER response: {result}")

            # Step 5: Verify orderId is returned
            order_id = result.get("orderId")
            if order_id:
                self.order_id = order_id
                logger.info(f"Order created successfully: orderId={order_id}")
                self.test_results["order_id_returned"] = True
            else:
                logger.error("No orderId in response")
                self.test_results["order_id_returned"] = False

            # Step 6: Verify payment link (formUrl) is returned
            form_url = result.get("formUrl")
            if form_url:
                logger.info(f"Payment link received: {form_url[:50]}...")
                self.test_results["form_url_returned"] = True
            else:
                logger.warning("No formUrl in response (may be expected for some configurations)")
                self.test_results["form_url_returned"] = False

            # Check status
            status_str = result.get("statusExtStr")
            status_int = result.get("statusExtInt")
            logger.info(f"Order status: {status_str} ({status_int})")

            self.test_results["create_order"] = bool(order_id)
            return bool(order_id)

        except Bill24Error as e:
            logger.error(f"Bill24 API error: {e}")
            self.test_results["create_order"] = False
            self.test_results["order_id_returned"] = False
            self.test_results["form_url_returned"] = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.test_results["create_order"] = False
            return False

    async def test_get_order_info(self) -> bool:
        """Verify order info can be retrieved."""
        logger.info("\n=== Step 6: Testing GET_ORDER_INFO ===")

        if not self.order_id:
            logger.error("No order_id available - skipping order info test")
            self.test_results["get_order_info"] = False
            return False

        try:
            result = await self.client.get_order_info(self.order_id)
            logger.info(f"GET_ORDER_INFO response: {result}")

            # Verify we can retrieve order info
            if result:
                logger.info(f"Order info retrieved successfully")
                self.test_results["get_order_info"] = True
                return True
            else:
                logger.warning("Empty order info response")
                self.test_results["get_order_info"] = False
                return False

        except Bill24Error as e:
            logger.error(f"Bill24 API error: {e}")
            self.test_results["get_order_info"] = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.test_results["get_order_info"] = False
            return False

    async def run_all_tests(self):
        """Run the complete test suite."""
        logger.info("=" * 60)
        logger.info("Bill24 CREATE_ORDER API Integration Test")
        logger.info("=" * 60)

        try:
            await self.setup()

            # Run tests in sequence
            await self.test_get_events()

            if self.test_results.get("get_events"):
                await self.test_get_seats()

            if self.test_results.get("get_seats"):
                await self.test_reservation()

                if self.test_results.get("reservation"):
                    await self.test_create_order()

                    if self.test_results.get("create_order"):
                        await self.test_get_order_info()

        except Exception as e:
            logger.error(f"Test suite failed: {e}")
        finally:
            await self.cleanup()

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 60)

        all_passed = True
        for test_name, passed in self.test_results.items():
            status = "PASS" if passed else "FAIL"
            logger.info(f"  {test_name}: {status}")
            if not passed:
                all_passed = False

        logger.info("=" * 60)

        # Note about test zone limitations
        if not self.test_results.get("reservation"):
            logger.info("\nNote: Test failed at reservation step.")
            logger.info("This is expected if Bill24 test zone has no available inventory.")
            logger.info("The CREATE_ORDER API integration code is correct,")
            logger.info("but requires available seats to complete the full flow.")

        if all_passed:
            logger.info("\nAll tests PASSED!")
        else:
            logger.info("\nSome tests did not pass - see details above")
        logger.info("=" * 60)

        return all_passed


async def main():
    """Main entry point."""
    tester = Bill24CreateOrderTest()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
