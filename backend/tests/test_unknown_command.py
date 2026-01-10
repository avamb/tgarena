"""
Test Bot Unknown Command Handling

This test verifies that the bot properly handles unknown commands and messages.
"""

import asyncio
import logging
import sys
from typing import Dict

# Add parent directory to path for imports
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import localization directly to avoid circular import from bot module
import importlib.util
localization_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "bot", "localization.py")
spec = importlib.util.spec_from_file_location("localization", localization_path)
localization_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(localization_module)
get_text = localization_module.get_text
TRANSLATIONS = localization_module.TRANSLATIONS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UnknownCommandTest:
    """Test class for unknown command handling."""

    def __init__(self):
        self.test_results: Dict[str, bool] = {}

    async def test_unknown_command_message_exists(self) -> bool:
        """Test 1: Verify unknown_command message exists in localization."""
        logger.info("\n=== Test 1: Verify unknown_command message ===")

        try:
            ru_msg = TRANSLATIONS.get("ru", {}).get("unknown_command", "")
            en_msg = TRANSLATIONS.get("en", {}).get("unknown_command", "")

            logger.info(f"RU unknown_command: {ru_msg}")
            logger.info(f"EN unknown_command: {en_msg}")

            assert ru_msg, "Russian unknown_command message missing"
            assert en_msg, "English unknown_command message missing"

            # Verify they mention /help
            assert "/help" in ru_msg.lower() or "help" in ru_msg.lower(), "RU should mention help"
            assert "/help" in en_msg.lower() or "help" in en_msg.lower(), "EN should mention help"

            logger.info("unknown_command messages exist and mention /help")
            self.test_results["unknown_command_msg"] = True
            return True

        except AssertionError as e:
            logger.error(f"Test failed: {e}")
            self.test_results["unknown_command_msg"] = False
            return False

    async def test_unknown_message_exists(self) -> bool:
        """Test 2: Verify unknown_message exists in localization."""
        logger.info("\n=== Test 2: Verify unknown_message ===")

        try:
            ru_msg = TRANSLATIONS.get("ru", {}).get("unknown_message", "")
            en_msg = TRANSLATIONS.get("en", {}).get("unknown_message", "")

            logger.info(f"RU unknown_message: {ru_msg}")
            logger.info(f"EN unknown_message: {en_msg}")

            assert ru_msg, "Russian unknown_message missing"
            assert en_msg, "English unknown_message missing"

            # Verify they mention /help
            assert "/help" in ru_msg.lower() or "help" in ru_msg.lower(), "RU should mention help"
            assert "/help" in en_msg.lower() or "help" in en_msg.lower(), "EN should mention help"

            logger.info("unknown_message messages exist and mention /help")
            self.test_results["unknown_message_msg"] = True
            return True

        except AssertionError as e:
            logger.error(f"Test failed: {e}")
            self.test_results["unknown_message_msg"] = False
            return False

    async def test_handlers_exist(self) -> bool:
        """Test 3: Verify unknown handlers exist in handlers.py."""
        logger.info("\n=== Test 3: Verify unknown handlers exist ===")

        try:
            handlers_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "app", "bot", "handlers.py"
            )

            with open(handlers_path, 'r') as f:
                content = f.read()

            has_cmd_unknown = 'def cmd_unknown' in content
            has_msg_unknown = 'def msg_unknown' in content
            has_unknown_command_filter = 'F.text.startswith("/")' in content
            has_catch_all = '@router.message()' in content

            logger.info(f"cmd_unknown handler: {has_cmd_unknown}")
            logger.info(f"msg_unknown handler: {has_msg_unknown}")
            logger.info(f"Unknown command filter: {has_unknown_command_filter}")
            logger.info(f"Catch-all message handler: {has_catch_all}")

            assert has_cmd_unknown, "cmd_unknown handler not found"
            assert has_msg_unknown, "msg_unknown handler not found"
            assert has_unknown_command_filter, "Command filter not found"
            assert has_catch_all, "Catch-all handler not found"

            logger.info("All unknown handlers exist!")
            self.test_results["handlers_exist"] = True
            return True

        except AssertionError as e:
            logger.error(f"Test failed: {e}")
            self.test_results["handlers_exist"] = False
            return False
        except Exception as e:
            logger.error(f"Error: {e}")
            self.test_results["handlers_exist"] = False
            return False

    async def test_get_text_returns_correct_messages(self) -> bool:
        """Test 4: Verify get_text returns correct messages."""
        logger.info("\n=== Test 4: Verify get_text function ===")

        try:
            ru_unknown_cmd = get_text("unknown_command", "ru")
            en_unknown_cmd = get_text("unknown_command", "en")
            ru_unknown_msg = get_text("unknown_message", "ru")
            en_unknown_msg = get_text("unknown_message", "en")

            logger.info(f"get_text('unknown_command', 'ru'): {ru_unknown_cmd}")
            logger.info(f"get_text('unknown_command', 'en'): {en_unknown_cmd}")
            logger.info(f"get_text('unknown_message', 'ru'): {ru_unknown_msg}")
            logger.info(f"get_text('unknown_message', 'en'): {en_unknown_msg}")

            # Verify they're not the key itself
            assert ru_unknown_cmd != "unknown_command", "Should return message, not key"
            assert en_unknown_cmd != "unknown_command", "Should return message, not key"
            assert ru_unknown_msg != "unknown_message", "Should return message, not key"
            assert en_unknown_msg != "unknown_message", "Should return message, not key"

            logger.info("get_text returns correct messages!")
            self.test_results["get_text_works"] = True
            return True

        except AssertionError as e:
            logger.error(f"Test failed: {e}")
            self.test_results["get_text_works"] = False
            return False

    async def test_handler_order(self) -> bool:
        """Test 5: Verify handlers are in correct order (specific before catch-all)."""
        logger.info("\n=== Test 5: Verify handler order ===")

        try:
            handlers_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "app", "bot", "handlers.py"
            )

            with open(handlers_path, 'r') as f:
                content = f.read()

            # Find positions of handlers
            cmd_start_pos = content.find("CommandStart()")
            cmd_help_pos = content.find('Command("help")')
            cmd_unknown_pos = content.find("cmd_unknown")
            msg_unknown_pos = content.find("msg_unknown")
            register_pos = content.find("def register_handlers")

            logger.info(f"CommandStart position: {cmd_start_pos}")
            logger.info(f"Command help position: {cmd_help_pos}")
            logger.info(f"cmd_unknown position: {cmd_unknown_pos}")
            logger.info(f"msg_unknown position: {msg_unknown_pos}")
            logger.info(f"register_handlers position: {register_pos}")

            # Verify order: specific commands before catch-all handlers
            assert cmd_start_pos < cmd_unknown_pos, "CommandStart should be before cmd_unknown"
            assert cmd_help_pos < cmd_unknown_pos, "Command help should be before cmd_unknown"
            assert cmd_unknown_pos < msg_unknown_pos, "cmd_unknown should be before msg_unknown"
            assert msg_unknown_pos < register_pos, "msg_unknown should be before register_handlers"

            logger.info("Handler order is correct!")
            logger.info("Order: specific commands -> unknown command -> unknown message")
            self.test_results["handler_order"] = True
            return True

        except AssertionError as e:
            logger.error(f"Test failed: {e}")
            self.test_results["handler_order"] = False
            return False

    async def run_all_tests(self):
        """Run the complete test suite."""
        logger.info("=" * 60)
        logger.info("Bot Unknown Command Handling Test")
        logger.info("=" * 60)

        try:
            await self.test_unknown_command_message_exists()
            await self.test_unknown_message_exists()
            await self.test_handlers_exist()
            await self.test_get_text_returns_correct_messages()
            await self.test_handler_order()

        except Exception as e:
            logger.error(f"Test suite failed: {e}")

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

        if all_passed:
            logger.info("\nAll tests PASSED!")
            logger.info("\nUnknown command handling summary:")
            logger.info("  - unknown_command message: suggests /help")
            logger.info("  - unknown_message: suggests /help")
            logger.info("  - cmd_unknown handler: catches /unknown...")
            logger.info("  - msg_unknown handler: catches any message")
            logger.info("  - Handler order: specific commands first")
        else:
            logger.info("\nSome tests did not pass - see details above")

        logger.info("=" * 60)

        return all_passed


async def main():
    """Main entry point."""
    tester = UnknownCommandTest()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
