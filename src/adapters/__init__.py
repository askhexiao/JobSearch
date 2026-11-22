# -*- coding: utf-8 -*-
"""适配器包。"""
from .base import BaseAdapter, FetchError
from .ncss_24365 import NCSSAdapter, AREA_CODES
from .greenhouse import GreenhouseAdapter, BOARDS

__all__ = [
    "BaseAdapter",
    "FetchError",
    "NCSSAdapter",
    "AREA_CODES",
    "GreenhouseAdapter",
    "BOARDS",
]
