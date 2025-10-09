#!/usr/bin/env python3
"""
Check and display configuration
"""

import sys
from config_manager import get_config

def main():
    print("Tamil Assistant - Configuration Check")
    print("=" * 60)
    print()

    try:
        config = get_config()
        print(config)
        print()
        print("✅ Configuration is valid!")
        return 0

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print()
        print("Run: ./setup.sh")
        return 1

    except ValueError as e:
        print(f"❌ Configuration errors found:")
        print()
        print(str(e))
        print()
        print("Please fix config.ini and try again")
        return 1

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
