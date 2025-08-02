#!/usr/bin/env python3
"""
S21 Debug Monitor - In-Place Sorted Command Display
Shows all S21 commands sorted by name, updating in place for easy change detection.
Uses hexadecimal display to avoid encoding issues.
"""

import time
import paho.mqtt.client as mqtt
from s21_common import S21Config, S21Parser, S21CommandTracker, clear_screen, format_timestamp, truncate_value, highlight_diff

class S21DebugMonitor:
    def __init__(self):
        # Load configuration
        self.config = S21Config()
        
        # Command tracker
        self.tracker = S21CommandTracker()
        
        # MQTT client
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(self.config.mqtt_username, self.config.mqtt_password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        self.running = False
        
    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback for MQTT connection"""
        if reason_code == 0:
            client.subscribe(self.config.tx_topic, qos=0)
            client.subscribe(self.config.rx_topic, qos=0)
            
            # Show initial interface
            self.update_display()
            
        else:
            print(f"Failed to connect to MQTT broker: {reason_code}")
            
    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        """Callback for MQTT disconnection"""
        pass
        
    def on_message(self, client, userdata, msg):
        """Callback for MQTT messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            direction = "TX" if topic.endswith('/tx') else "RX"
            
            # Parse the S21 packet(s)
            packets = S21Parser.parse_s21_packet(payload)
            if not packets:
                return
                
            # Process each command found in the JSON
            has_changes = False
            for packet in packets:
                command = packet['command']
                hex_value = packet['payload']  # Already converted to hex in parser
                timestamp = packet['timestamp']
                
                # Update command and check if it changed
                if self.tracker.update_command(command, hex_value, direction, timestamp, packet.get('dump', '')):
                    has_changes = True
            
            # Only update display if there were actual changes
            if has_changes:
                self.update_display()
                    
        except Exception as e:
            pass
            
    def update_display(self):
        """Update the display with current values"""
        # Clear screen completely
        clear_screen()
        
        # Header
        print("S21 Protocol Monitor")
        print("=" * 100)
        
        if not self.tracker.commands:
            print("\nWaiting for S21 commands...")
        else:
            # Get sorted commands
            sorted_commands = self.tracker.get_sorted_commands()
            
            print(f"\nAll Commands (Total: {len(self.tracker.commands)}):")
            print("-" * 100)
            print(f"{'CMD':<8} {'DIR':<4} {'HEX VALUE':<20} {'DUMP':<25} {'TIME':<10}")
            print("-" * 100)
            
            for command, data in sorted_commands:
                value = data['value']
                direction = data['direction']
                timestamp = format_timestamp(data['timestamp'])
                dump = data.get('dump', '')
                
                # Truncate long values
                display_value = truncate_value(value, 18)
                display_dump = truncate_value(dump, 23)
                
                print(f"{command:<8} {direction:<4} {display_value:<20} {display_dump:<25} {timestamp:<10}")
        
        # Show recent changes
        if self.tracker.recent_changes:
            print("\n" + "=" * 100)
            print("RECENT CHANGES")
            print("-" * 100)
            
            for change in self.tracker.recent_changes[-5:]:  # Show last 5
                cmd = change['command']
                direction = change['direction']
                timestamp = format_timestamp(change['timestamp'])
                
                # Show value change if it actually changed
                if change.get('value_changed', True):
                    old_val = change['old_value']
                    new_val = change['new_value']
                    old_val_highlighted, new_val_highlighted = highlight_diff(old_val, new_val)
                    print(f"{cmd:<8} {direction:<4} VALUE: {old_val_highlighted} → {new_val_highlighted} [{timestamp}]")
                
                # Show dump change if it actually changed
                if change.get('dump_changed', True):
                    old_dump = change.get('old_dump', '')
                    new_dump = change.get('new_dump', '')
                    if old_dump or new_dump:  # Show if either has content
                        old_dump_highlighted, new_dump_highlighted = highlight_diff(old_dump, new_dump)
                        old_dump_short = truncate_value(old_dump_highlighted, 35)
                        new_dump_short = truncate_value(new_dump_highlighted, 35)
                        print(f"{'':>12}  DUMP:  {old_dump_short} → {new_dump_short}")
                
                print()  # Empty line between changes
            
    def run(self):
        """Main monitoring loop"""
        try:
            # Connect to MQTT
            self.client.connect(self.config.mqtt_host, self.config.mqtt_port, 60)
            self.client.loop_start()
            
            # Wait for connection
            time.sleep(2)
            
            self.running = True
            
            # Main loop - run continuously until Ctrl+C
            try:
                while self.running:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                self.running = False
                
        except Exception:
            pass
        finally:
            self.running = False
            self.client.loop_stop()
            self.client.disconnect()
            print("\n\nDebug monitoring stopped.")


def main():
    """Main entry point"""
    monitor = S21DebugMonitor()
    monitor.run()


if __name__ == "__main__":
    main()