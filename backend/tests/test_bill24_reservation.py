"""
Test Bill24 RESERVATION API Integration

This script tests the seat reservation functionality via the Bill24/TixGear API.
It uses the official test credentials to verify the complete reservation flow.

Test Steps:
1. Get events from Bill24 API
2. Get seat list for an event
3. Reserve a seat using RESERVATION command
4. Verify cart timeout is returned
5. Verify seat is marked as reserved
6. Unreserve the seat (cleanup)
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
TEST_USER_ID = 33922
TEST_SESSION_ID = "7c696b4af364928202dd"
TEST_ZONE = "test"


class Bill24ReservationTest:
    """Test class for Bill24 RESERVATION API integration."""

    def __init__(self):
        self.client: Optional[Bill24Client] = None
        self.test_results: Dict[str, bool] = {}
        self.reserved_seats: List[int] = []
        self.action_event_id: Optional[int] = None
        self.first_seat_data: Optional[Dict[str, Any]] = None

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

        # Try to create a new user to get a valid session
        try:
            logger.info("Creating test user to get valid session...")
            import random
            test_chat_id = random.randint(100000000, 999999999)
            result = await self.client.create_user(
                telegram_chat_id=test_chat_id,
                first_name="Test",
                last_name="User"
            )
            user_id = result.get("userId")
            session_id = result.get("sessionId")
            if user_id and session_id:
                logger.info(f"Got new session: userId={user_id}, sessionId={session_id[:10]}...")
                # Update client with session
                self.client.user_id = user_id
                self.client.session_id = session_id
            else:
                logger.warning("CREATE_USER didn't return session, trying static credentials")
                self.client.user_id = TEST_USER_ID
                self.client.session_id = TEST_SESSION_ID
        except Exception as e:
            logger.warning(f"CREATE_USER failed: {e}")
            logger.info("Using static test credentials")
            self.client.user_id = TEST_USER_ID
            self.client.session_id = TEST_SESSION_ID

    async def cleanup(self):
        """Clean up resources and unreserve any reserved seats."""
        if self.client:
            # Unreserve any seats we reserved during testing
            if self.reserved_seats and self.action_event_id:
                try:
                    logger.info(f"Cleaning up - unreserving seats: {self.reserved_seats}")
                    await self.client.unreserve_all(self.action_event_id)
                except Exception as e:
                    logger.warning(f"Cleanup failed: {e}")

            await self.client.close()
        logger.info("Cleanup complete")

    async def test_get_events(self) -> bool:
        """Step 1: Get events from Bill24 API."""
        logger.info("\n=== Step 1: Testing GET_ALL_ACTIONS ===")
        try:
            response = await self.client.get_all_actions()

            # Check if we got events
            action_list = response.get("actionList", [])
            logger.info(f"Retrieved {len(action_list)} events")

            if len(action_list) > 0:
                # Try to find an event with future dates or active sessions
                from datetime import datetime
                today = datetime.now()

                for action in action_list:
                    action_event_list = action.get("actionEventList", [])
                    if not action_event_list:
                        continue

                    # Try each action event to find one that might work
                    for event in action_event_list:
                        event_date_str = event.get("day", "")
                        try:
                            # Try parsing date (format: DD.MM.YYYY)
                            if event_date_str:
                                event_date = datetime.strptime(event_date_str, "%d.%m.%Y")
                                # Skip old events
                                if event_date < today:
                                    continue
                        except ValueError:
                            pass  # If parsing fails, still try this event

                        self.action_event_id = event.get("actionEventId")
                        logger.info(f"Selected event: {action.get('name', 'N/A')}")
                        logger.info(f"  Action ID: {action.get('actionId')}")
                        logger.info(f"  Session ID: {self.action_event_id}")
                        logger.info(f"  Date: {event.get('day')} {event.get('time')}")
                        break

                    if self.action_event_id:
                        break

                # If no future event found, just use the first one available
                if not self.action_event_id:
                    first_action = action_list[0]
                    action_event_list = first_action.get("actionEventList", [])
                    if action_event_list:
                        self.action_event_id = action_event_list[0].get("actionEventId")
                        logger.info(f"Using first available event (may be past): {first_action.get('name', 'N/A')}")
                        logger.info(f"  Session ID: {self.action_event_id}")

                # Log a few events for reference
                logger.info(f"\nSample events available:")
                for i, action in enumerate(action_list[:5]):
                    events = action.get("actionEventList", [])
                    if events:
                        logger.info(f"  {i+1}. {action.get('name', 'N/A')} - ID:{action.get('actionId')} - Sessions: {len(events)}")
                        for ev in events[:2]:
                            logger.info(f"      Session {ev.get('actionEventId')}: {ev.get('day')} {ev.get('time')}")

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
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.test_results["get_events"] = False
            return False

    async def test_get_seats(self) -> bool:
        """Step 2: Get available seats for an event."""
        logger.info("\n=== Step 2: Testing GET_SEAT_LIST ===")

        if not self.action_event_id:
            logger.error("No action_event_id available - skipping seat test")
            self.test_results["get_seats"] = False
            return False

        # Try to get seat list, may need to try different events
        events_to_try = [self.action_event_id]

        # Get more events to try if the first one fails
        try:
            response = await self.client.get_all_actions()
            action_list = response.get("actionList", [])
            for action in action_list[:20]:  # Try first 20 actions
                for event in action.get("actionEventList", [])[:3]:  # First 3 sessions each
                    event_id = event.get("actionEventId")
                    if event_id and event_id not in events_to_try:
                        events_to_try.append(event_id)
        except:
            pass

        logger.info(f"Will try up to {len(events_to_try)} event sessions to find available seats")

        for event_id in events_to_try[:10]:  # Limit to 10 attempts
            try:
                logger.info(f"Trying event session ID: {event_id}")
                seats = await self.client.get_seat_list(event_id)
                logger.info(f"Retrieved {len(seats)} seats for event {event_id}")

                if len(seats) > 0:
                    # Find available seats
                    # Check the 'available' field - this is the key indicator
                    available_seats = []
                    for s in seats:
                        is_available = s.get("available", True)  # Default to True if not specified
                        status = s.get("status", "").upper()
                        is_free = s.get("free", False)
                        is_reserved = s.get("reserved", False)

                        # Seat is available if:
                        # - 'available' is True, OR
                        # - 'free' is True, OR
                        # - status is "FREE", AND
                        # - not reserved
                        if is_available or is_free or (status == "FREE" and not is_reserved):
                            available_seats.append(s)

                    logger.info(f"Total seats: {len(seats)}, Available: {len(available_seats)}")

                    if available_seats:
                        first_seat = available_seats[0]
                        logger.info(f"First available seat (full data): {first_seat}")
                        logger.info(f"First available seat:")
                        logger.info(f"  Seat ID: {first_seat.get('seatId')}")
                        logger.info(f"  Category Price ID: {first_seat.get('categoryPriceId')}")
                        logger.info(f"  Sector: {first_seat.get('sector', 'N/A')}")
                        logger.info(f"  Row: {first_seat.get('row', 'N/A')}")
                        logger.info(f"  Seat: {first_seat.get('seat', 'N/A')}")
                        logger.info(f"  Price: {first_seat.get('price', 'N/A')}")
                        logger.info(f"  Status: {first_seat.get('status', 'N/A')}")
                        logger.info(f"  Placement: {first_seat.get('placement', 'N/A')}")

                        # Store seat data for reservation test
                        self.reserved_seats = [first_seat.get('seatId')]
                        self.first_seat_data = first_seat
                        self.action_event_id = event_id

                        self.test_results["get_seats"] = True
                        return True
                    else:
                        logger.info(f"No available seats in event {event_id}, trying next...")
                else:
                    logger.info(f"No seats returned for event {event_id}, trying next...")

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
        """Step 3-5: Test RESERVATION command."""
        logger.info("\n=== Step 3: Testing RESERVATION ===")

        if not self.action_event_id:
            logger.error("Missing action_event_id - skipping reservation test")
            self.test_results["reservation"] = False
            return False

        if not self.first_seat_data:
            logger.error("Missing seat data - skipping reservation test")
            self.test_results["reservation"] = False
            return False

        try:
            # Check if this is a placement seat or entry ticket
            is_placement = self.first_seat_data.get("placement", False)
            seat_id = self.first_seat_data.get("seatId")
            category_price_id = self.first_seat_data.get("categoryPriceId")

            if is_placement:
                # For seats with specific placement, use seatList
                logger.info(f"Reserving placement seat: {seat_id} for event {self.action_event_id}")
                params = {
                    "actionEventId": self.action_event_id,
                    "seatList": [seat_id],
                    "type": "RESERVE",
                }
            else:
                # For entry tickets (no placement), use categoryList
                logger.info(f"Reserving entry ticket: categoryPriceId={category_price_id} for event {self.action_event_id}")
                params = {
                    "actionEventId": self.action_event_id,
                    "categoryList": [{"categoryPriceId": category_price_id, "quantity": 1}],
                    "type": "RESERVE",
                }

            logger.info(f"RESERVATION params: {params}")
            raw_response = await self.client._request("RESERVATION", params)
            logger.info(f"Full RESERVATION response: {raw_response}")

            result = {
                "seatList": raw_response.get("seatList", []),
                "cartTimeout": raw_response.get("cartTimeout", 0),
                "totalSum": raw_response.get("totalSum", 0),
            }

            logger.info("Parsed reservation response:")
            logger.info(f"  Seat list: {result.get('seatList', [])}")
            logger.info(f"  Cart timeout: {result.get('cartTimeout')} seconds")
            logger.info(f"  Total sum: {result.get('totalSum')}")

            # Step 4: Verify cart timeout is returned
            cart_timeout = result.get("cartTimeout", 0)
            if cart_timeout > 0:
                logger.info(f"✓ Cart timeout verified: {cart_timeout} seconds")
                self.test_results["cart_timeout"] = True
            else:
                logger.warning("Cart timeout not returned or is 0")
                self.test_results["cart_timeout"] = False

            # Step 5: Verify seat is marked as reserved
            seat_list = result.get("seatList", [])
            if seat_list:
                logger.info(f"✓ Seats reserved successfully: {len(seat_list)} seats")
                self.test_results["seat_reserved"] = True
            else:
                logger.warning("No seats in reservation response")
                self.test_results["seat_reserved"] = False

            self.test_results["reservation"] = True
            return True

        except Bill24SessionError as e:
            logger.error(f"Session error: {e}")
            logger.info("This may indicate the test session has expired")
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

    async def test_get_cart(self) -> bool:
        """Verify cart contains reserved seats."""
        logger.info("\n=== Verifying Cart Contents ===")

        try:
            cart = await self.client.get_cart()
            logger.info(f"Cart response: {cart}")

            # Check for reserved items in cart
            action_event_list = cart.get("actionEventList", [])
            total_sum = cart.get("totalSum", 0)
            time_remaining = cart.get("time", 0)

            logger.info(f"Cart contents:")
            logger.info(f"  Events in cart: {len(action_event_list)}")
            logger.info(f"  Total sum: {total_sum}")
            logger.info(f"  Time remaining: {time_remaining} seconds")

            self.test_results["get_cart"] = len(action_event_list) > 0
            return self.test_results["get_cart"]

        except Bill24Error as e:
            logger.error(f"Bill24 API error: {e}")
            self.test_results["get_cart"] = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.test_results["get_cart"] = False
            return False

    async def test_unreserve(self) -> bool:
        """Cleanup: Unreserve the seats."""
        logger.info("\n=== Cleanup: Testing UN_RESERVE_ALL ===")

        if not self.action_event_id:
            logger.info("No reservation to clean up")
            return True

        try:
            result = await self.client.unreserve_all(self.action_event_id)
            logger.info(f"Unreserve response: {result}")
            logger.info("✓ Seats unreserved successfully")
            self.test_results["unreserve"] = True
            self.reserved_seats = []  # Clear so cleanup doesn't try again
            return True

        except Bill24Error as e:
            logger.error(f"Bill24 API error: {e}")
            self.test_results["unreserve"] = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.test_results["unreserve"] = False
            return False

    async def run_all_tests(self):
        """Run the complete test suite."""
        logger.info("=" * 60)
        logger.info("Bill24 RESERVATION API Integration Test")
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
                    await self.test_get_cart()
                    await self.test_unreserve()

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
            status = "✓ PASS" if passed else "✗ FAIL"
            logger.info(f"  {test_name}: {status}")
            if not passed:
                all_passed = False

        logger.info("=" * 60)
        if all_passed:
            logger.info("All tests PASSED!")
        else:
            logger.info("Some tests FAILED - see details above")
        logger.info("=" * 60)

        return all_passed


async def main():
    """Main entry point."""
    tester = Bill24ReservationTest()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
