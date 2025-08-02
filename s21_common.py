#!/usr/bin/env python3
"""
S21 Common Library
Shared functionality for S21 protocol monitoring tools.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class S21Config:
    """Configuration management for S21 tools"""

    def __init__(self):
        self.mqtt_host = os.getenv('MQTT_HOST', 'homeassistant.local')
        self.mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
        self.mqtt_username = os.getenv('MQTT_USERNAME', 'homeassistant')
        self.mqtt_password = os.getenv('MQTT_PASSWORD')

        self.base_path = os.getenv('DEVICE_ID')
        self.tx_topic = f"info/{self.base_path}/tx"
        self.rx_topic = f"info/{self.base_path}/rx"


class S21Parser:
    """S21 protocol packet parser"""

    @staticmethod
    def parse_s21_packet(data: str) -> List[Dict[str, Any]]:
        """Parse S21 JSON data from MQTT"""
        if not data:
            return []

        try:
            # Parse JSON data directly
            json_data = json.loads(data)

            if json_data.get('protocol') == 'S21':
                # Extract dump field and all S21 commands from the JSON
                commands = []
                dump_data = json_data.get('dump', '')

                for key, value in json_data.items():
                    if key not in ['protocol', 'dump'] and len(key) >= 2:
                        # Convert value to hex representation for clean display
                        hex_value = S21Parser.to_hex_string(value)

                        commands.append({
                            'command': key,
                            'payload': hex_value,
                            'raw_payload': str(value) if value else '',
                            'dump': dump_data,
                            'raw': data,
                            'timestamp': datetime.now()
                        })

                return commands

            return []
        except (json.JSONDecodeError, Exception):
            return []

    @staticmethod
    def to_hex_string(value) -> str:
        """Convert a value to a clean hex string representation"""
        if not value:
            return ""

        try:
            # Convert everything to hex for consistency
            if isinstance(value, str):
                # Convert each character to hex
                return ''.join(f'{ord(c):02X}' for c in value)
            else:
                # Convert other types to string first, then to hex
                str_value = str(value)
                return ''.join(f'{ord(c):02X}' for c in str_value)
        except Exception:
            # Fallback: convert to string and then hex
            try:
                str_value = str(value)
                return ''.join(f'{ord(c):02X}' for c in str_value)
            except:
                return "ERROR"


def highlight_diff(old_str: str, new_str: str) -> tuple[str, str]:
    """Highlight differences in both strings using inverted colors.

    Returns:
        tuple: (highlighted_old, highlighted_new)
    """
    if old_str == new_str:
        return old_str, new_str

    # ANSI escape codes for inverted colors
    INVERT = '\033[7m'  # Invert colors
    RESET = '\033[0m'   # Reset to normal

    old_result = []
    new_result = []
    max_len = max(len(old_str), len(new_str))

    for i in range(max_len):
        old_char = old_str[i] if i < len(old_str) else ''
        new_char = new_str[i] if i < len(new_str) else ''

        if old_char != new_char:
            # Highlight changed characters in both strings
            if old_char:
                old_result.append(f"{INVERT}{old_char}{RESET}")
            if new_char:
                new_result.append(f"{INVERT}{new_char}{RESET}")
        else:
            # Keep unchanged characters as-is
            old_result.append(old_char)
            new_result.append(new_char)

    return ''.join(old_result), ''.join(new_result)


class S21CommandTracker:
    """Track and manage S21 command states"""

    def __init__(self):
        self.commands = {}  # {command: {'value': str, 'direction': str, 'timestamp': datetime}}
        self.recent_changes = []  # List of recent changes, max 5

    def update_command(self, command: str, value: str, direction: str, timestamp: datetime, dump: str = '') -> bool:
        """Update a command value and return True if it changed"""
        # Check if this is a real change
        old_value = None
        old_dump = ''

        if command in self.commands:
            old_value = self.commands[command]['value']
            old_dump = self.commands[command].get('dump', '')
            value_changed = self.commands[command]['value'] != value
            dump_changed = old_dump != dump
            direction_changed = self.commands[command]['direction'] != direction
            changed = value_changed or dump_changed or direction_changed
        else:
            changed = True  # New command
            value_changed = True
            dump_changed = True

        # Record the change if value OR dump changed (not just new commands)
        if changed and old_value is not None and (value_changed or dump_changed):
            change_record = {
                'command': command,
                'old_value': old_value,
                'new_value': value,
                'old_dump': old_dump,
                'new_dump': dump,
                'direction': direction,
                'timestamp': timestamp,
                'value_changed': value_changed,
                'dump_changed': dump_changed
            }
            self.recent_changes.append(change_record)

            # Keep only last 5 changes
            if len(self.recent_changes) > 5:
                self.recent_changes.pop(0)

        self.commands[command] = {
            'value': value,
            'direction': direction,
            'timestamp': timestamp,
            'dump': dump
        }

        return changed

    def get_sorted_commands(self) -> List[tuple]:
        """Get commands sorted alphabetically"""
        return sorted(self.commands.items())


def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')


def format_timestamp(dt: datetime) -> str:
    """Format timestamp for display"""
    return dt.strftime("%H:%M:%S")


def truncate_value(value: str, max_length: int = 20) -> str:
    """Truncate a value for display"""
    if len(value) > max_length:
        return value[:max_length-3] + "..."
    return value
