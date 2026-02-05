"""
Paradox Serial Interface

Interface Python para comunicação com centrais de alarme Paradox (MG/SP/Digiplex)
via porta serial TTL.

Baseado na engenharia reversa do projeto ParadoxAlarmInterface/pai.
"""

__version__ = "0.1.0"
__author__ = "Paradox Serial Interface Project"

from .connection import SerialConnection
from .panel import ParadoxPanel
from . import protocol
from . import commands

__all__ = [
    'SerialConnection',
    'ParadoxPanel',
    'protocol',
    'commands',
]
