#!/usr/bin/env python3
"""Start the Slack connector for the digital twin."""

import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

from phase4_platform.connectors.messaging import SlackConnector

if __name__ == "__main__":
    connector = SlackConnector()
    connector.start()
