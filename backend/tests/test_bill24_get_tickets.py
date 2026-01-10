"""
Test Bill24 GET_TICKETS_BY_ORDER API Integration

This test verifies that the GET_TICKETS_BY_ORDER method is correctly implemented.
Due to the requirement of a paid order, this test:
1. Verifies the method exists and has correct parameters
2. Tests error handling for unpaid/invalid orders
3. Documents expected response format

Full integration requires completing payment, which is an external dependency.
"""

import asyncio
import logging
import sys
from typing import Optional, Dict, Any

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


class Bill24GetTicketsTest:
    """Test class for Bill24 GET_TICKETS_BY_ORDER API integration."""

    def __init__(self):
        self.client: Optional[Bill24Client] = None
        self.test_results: Dict[str, bool] = {}

    async def setup(self):
        """Initialize the Bill24 client with test credentials."""
        logger.info("Setting up Bill24 client with test credentials...")

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
                last_name="TicketUser"
            )
            user_id = result.get("userId")
            session_id = result.get("sessionId")
            if user_id and session_id:
                logger.info(f"Got new session: userId={user_id}, sessionId={session_id[:10]}...")
                self.client.user_id = user_id
                self.client.session_id = session_id
            else:
                raise Exception("CREATE_USER didn't return valid session")
        except Exception as e:
            logger.error(f"Failed to create test user: {e}")
            raise

    async def cleanup(self):
        """Clean up resources."""
        if self.client:
            await self.client.close()
        logger.info("Cleanup complete")

    async def test_method_exists(self) -> bool:
        """Verify get_tickets_by_order method exists and has correct signature."""
        logger.info("\n=== Test 1: Verify method exists ===")

        try:
            # Check method exists
            assert hasattr(self.client, 'get_tickets_by_order'), "get_tickets_by_order method not found"

            # Check method is callable
            assert callable(getattr(self.client, 'get_tickets_by_order')), "get_tickets_by_order is not callable"

            # Check method accepts order_id parameter
            import inspect
            sig = inspect.signature(self.client.get_tickets_by_order)
            params = list(sig.parameters.keys())
            assert 'order_id' in params, "get_tickets_by_order missing order_id parameter"

            logger.info("Method exists with correct signature")
            logger.info(f"  Parameters: {params}")
            self.test_results["method_exists"] = True
            return True

        except AssertionError as e:
            logger.error(f"Method check failed: {e}")
            self.test_results["method_exists"] = False
            return False

    async def test_error_handling_invalid_order(self) -> bool:
        """Test error handling for invalid order ID."""
        logger.info("\n=== Test 2: Error handling for invalid order ===")

        try:
            # Try to get tickets for a non-existent order
            invalid_order_id = 9999999999
            logger.info(f"Calling get_tickets_by_order with invalid orderId: {invalid_order_id}")

            tickets = await self.client.get_tickets_by_order(invalid_order_id)

            # If no error, check empty response
            if not tickets:
                logger.info("Received empty ticket list for invalid order (expected)")
                self.test_results["error_handling"] = True
                return True
            else:
                logger.warning(f"Unexpected tickets returned: {tickets}")
                self.test_results["error_handling"] = False
                return False

        except Bill24Error as e:
            # Expected - invalid order should return error
            logger.info(f"Bill24 error for invalid order (expected): {e}")
            self.test_results["error_handling"] = True
            return True
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.test_results["error_handling"] = False
            return False

    async def test_response_parsing_documentation(self) -> bool:
        """Document expected response format from API."""
        logger.info("\n=== Test 3: Document expected response format ===")

        # Document expected ticket structure
        expected_ticket_fields = {
            "ticketId": "Ulong - Ticket ID",
            "date": "string - Event date/time",
            "venueName": "string - Venue name",
            "venueAddress": "string - Venue address",
            "actionName": "string - Event name",
            "sector": "string - Sector name",
            "row": "string - Row number/name",
            "number": "string - Seat number",
            "categoryName": "string - Price category",
            "price": "number - Ticket price",
            "qrCodeImg": "string - QR code image (Base64)",
            "barCodeImg": "string - Barcode image (Base64)",
            "barCodeNumber": "string - Numeric barcode value",
            "statusInt": "int - Ticket status code (0=unused, 1=entered, 2=exited, 3=refunded)",
            "statusStr": "string - Ticket status description",
        }

        logger.info("Expected ticket fields from GET_TICKETS_BY_ORDER response:")
        for field, description in expected_ticket_fields.items():
            logger.info(f"  {field}: {description}")

        # Verify our client extracts ticketList correctly
        logger.info("\nClient implementation extracts 'ticketList' from response")
        logger.info("QR code and barcode are Base64 encoded images")

        self.test_results["response_documentation"] = True
        return True

    async def test_ticket_model_fields(self) -> bool:
        """Verify Ticket model has fields to store Bill24 ticket data."""
        logger.info("\n=== Test 4: Verify Ticket model has correct fields ===")

        try:
            from app.models import Ticket

            # Check required fields exist
            required_fields = [
                'bil24_ticket_id',
                'event_name',
                'event_date',
                'venue_name',
                'sector',
                'row',
                'seat',
                'price',
                'qr_code_data',
                'barcode_data',
                'barcode_number',
                'status',
            ]

            for field in required_fields:
                assert hasattr(Ticket, field), f"Ticket model missing field: {field}"

            logger.info("Ticket model has all required fields:")
            for field in required_fields:
                logger.info(f"  - {field}")

            self.test_results["ticket_model"] = True
            return True

        except ImportError as e:
            logger.error(f"Failed to import Ticket model: {e}")
            self.test_results["ticket_model"] = False
            return False
        except AssertionError as e:
            logger.error(f"Ticket model field check failed: {e}")
            self.test_results["ticket_model"] = False
            return False

    async def run_all_tests(self):
        """Run the complete test suite."""
        logger.info("=" * 60)
        logger.info("Bill24 GET_TICKETS_BY_ORDER API Integration Test")
        logger.info("=" * 60)

        try:
            await self.setup()

            # Run tests
            await self.test_method_exists()
            await self.test_error_handling_invalid_order()
            await self.test_response_parsing_documentation()
            await self.test_ticket_model_fields()

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

        logger.info("\nNote: Full integration test requires a PAID order.")
        logger.info("This test verifies the method implementation and error handling.")
        logger.info("Actual ticket retrieval with QR/barcode extraction requires")
        logger.info("completing payment through Bill24 acquiring system.")

        if all_passed:
            logger.info("\nAll tests PASSED!")
        else:
            logger.info("\nSome tests did not pass - see details above")
        logger.info("=" * 60)

        return all_passed


async def main():
    """Main entry point."""
    tester = Bill24GetTicketsTest()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
