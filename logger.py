#!/usr/bin/env python3
"""
Logging configuration for streaming output to frontend.
Ensures Python prints are unbuffered and immediately visible.
"""
import sys
import io

def configure_logging():
    """Configure Python stdout/stderr for unbuffered real-time output."""
    try:
        # Make stdout/stderr unbuffered
        sys.stdout = io.TextIOWrapper(
            buffer=sys.stdout.buffer if hasattr(sys.stdout, 'buffer') else sys.stdout,
            encoding=sys.stdout.encoding or 'utf-8',
            line_buffering=True
        )
        if sys.stderr:
            sys.stderr = io.TextIOWrapper(
                buffer=sys.stderr.buffer if hasattr(sys.stderr, 'buffer') else sys.stderr,
                encoding=sys.stderr.encoding or 'utf-8',
                line_buffering=True
            )
    except:
        # Fallback: set PYTHONUNBUFFERED
        os.environ['PYTHONUNBUFFERED'] = '1'

# Configure on import
configure_logging()
