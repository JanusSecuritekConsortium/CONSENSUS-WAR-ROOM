#!/usr/bin/env python3
"""
Compatibility launcher for CONSENSUS War Room Genesis.

The implementation now lives under core/, config/, ui/, and integrations/.
Keep this file as the stable command target for existing Msty setup docs,
batch files, and older local workflows.
"""

from core.cli import main


if __name__ == "__main__":
    main()

