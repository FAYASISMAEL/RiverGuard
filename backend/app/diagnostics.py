"""Log error locations without printing database URLs, tokens, or SQL values."""
import logging
import traceback

def log_failure(context, exc):
    frames = '\n'.join(f'  {frame.filename}:{frame.lineno} in {frame.name}' for frame in traceback.extract_tb(exc.__traceback__))
    logging.error('%s (%s)\n%s', context, type(exc).__name__, frames)
