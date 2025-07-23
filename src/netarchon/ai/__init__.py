"""
NetArchon AI Coordination Framework

This module provides AI-powered capabilities for NetArchon including:
- Natural language interface for multi-device commands
- Task automation and scheduling
- Predictive maintenance recommendations
- Autonomous problem detection and resolution
"""

from .coordinator import KiroAICoordinator
from .nlp_interface import NaturalLanguageInterface
from .task_automation import TaskAutomationEngine
from .predictive_maintenance import PredictiveMaintenanceEngine
from .autonomous_detection import AutonomousProblemDetector

__all__ = [
    'KiroAICoordinator',
    'NaturalLanguageInterface', 
    'TaskAutomationEngine',
    'PredictiveMaintenanceEngine',
    'AutonomousProblemDetector'
]