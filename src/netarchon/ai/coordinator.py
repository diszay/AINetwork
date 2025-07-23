"""
Kiro AI Coordination Framework

Central coordinator for AI-powered network management capabilities.
Integrates natural language processing, task automation, predictive maintenance,
and autonomous problem detection for omniscient network intelligence.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

from .nlp_interface import NaturalLanguageInterface
from .task_automation import TaskAutomationEngine
from .predictive_maintenance import PredictiveMaintenanceEngine
from .autonomous_detection import AutonomousProblemDetector
from ..monitoring.storage import MetricStorageManager
from ..monitoring.alerts import EnhancedAlertManager


class TaskPriority(Enum):
    """Task priority levels for AI coordination"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AITask:
    """AI task representation"""
    task_id: str
    description: str
    task_type: str
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parameters: Dict[str, Any] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class KiroAICoordinator:
    """
    Central AI coordinator for NetArchon's intelligent capabilities.
    
    Orchestrates natural language processing, task automation,
    predictive maintenance, and autonomous problem detection.
    """
    
    def __init__(self, 
                 storage_manager: MetricStorageManager,
                 alert_manager: EnhancedAlertManager,
                 config: Dict[str, Any] = None):
        """
        Initialize the Kiro AI Coordinator.
        
        Args:
            storage_manager: Metrics storage for historical data
            alert_manager: Alert system for notifications
            config: AI configuration parameters
        """
        self.storage_manager = storage_manager
        self.alert_manager = alert_manager
        self.config = config or {}
        
        # Initialize AI components
        self.nlp_interface = NaturalLanguageInterface(self.config.get('nlp', {}))
        self.task_engine = TaskAutomationEngine(self.config.get('automation', {}))
        self.predictive_engine = PredictiveMaintenanceEngine(
            storage_manager, self.config.get('predictive', {})
        )
        self.detection_engine = AutonomousProblemDetector(
            storage_manager, alert_manager, self.config.get('detection', {})
        )
        
        # Task management
        self.active_tasks: Dict[str, AITask] = {}
        self.task_queue: List[AITask] = []
        self.task_history: List[AITask] = []
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Coordination state
        self.is_running = False
        self.coordination_loop_task = None
        
        self.logger = logging.getLogger(__name__)
        
    async def start(self):
        """Start the AI coordination system"""
        if self.is_running:
            return
            
        self.logger.info("Starting Kiro AI Coordinator...")
        
        # Start AI components
        await self.nlp_interface.initialize()
        await self.task_engine.start()
        await self.predictive_engine.start()
        await self.detection_engine.start()
        
        # Start coordination loop
        self.is_running = True
        self.coordination_loop_task = asyncio.create_task(self._coordination_loop())
        
        self.logger.info("Kiro AI Coordinator started successfully")
        
    async def stop(self):
        """Stop the AI coordination system"""
        if not self.is_running:
            return
            
        self.logger.info("Stopping Kiro AI Coordinator...")
        
        self.is_running = False
        
        # Cancel coordination loop
        if self.coordination_loop_task:
            self.coordination_loop_task.cancel()
            try:
                await self.coordination_loop_task
            except asyncio.CancelledError:
                pass
                
        # Stop AI components
        await self.detection_engine.stop()
        await self.predictive_engine.stop()
        await self.task_engine.stop()
        
        self.logger.info("Kiro AI Coordinator stopped")
        
    async def process_natural_language_command(self, command: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a natural language command and execute appropriate actions.
        
        Args:
            command: Natural language command from user
            context: Additional context for command processing
            
        Returns:
            Command processing result
        """
        try:
            # Parse the natural language command
            parsed_command = await self.nlp_interface.parse_command(command, context)
            
            if not parsed_command.get('valid'):
                return {
                    'success': False,
                    'error': 'Could not understand the command',
                    'suggestion': parsed_command.get('suggestion')
                }
            
            # Create and queue AI task
            task = AITask(
                task_id=f"nlp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description=f"Natural language command: {command}",
                task_type="nlp_command",
                priority=TaskPriority.HIGH,
                status=TaskStatus.PENDING,
                created_at=datetime.now(),
                parameters={
                    'command': command,
                    'parsed_command': parsed_command,
                    'context': context
                }
            )
            
            await self._queue_task(task)
            
            return {
                'success': True,
                'task_id': task.task_id,
                'parsed_command': parsed_command,
                'message': 'Command queued for execution'
            }
            
        except Exception as e:
            self.logger.error(f"Error processing natural language command: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def schedule_maintenance_task(self, device_id: str, maintenance_type: str, 
                                      scheduled_time: datetime = None) -> Dict[str, Any]:
        """
        Schedule a predictive maintenance task.
        
        Args:
            device_id: Target device identifier
            maintenance_type: Type of maintenance to perform
            scheduled_time: When to execute the task
            
        Returns:
            Task scheduling result
        """
        try:
            # Get predictive maintenance recommendations
            recommendations = await self.predictive_engine.get_maintenance_recommendations(device_id)
            
            if maintenance_type not in [r['type'] for r in recommendations]:
                return {
                    'success': False,
                    'error': f'Maintenance type {maintenance_type} not recommended for device {device_id}'
                }
            
            # Create maintenance task
            task = AITask(
                task_id=f"maint_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description=f"Predictive maintenance: {maintenance_type} for {device_id}",
                task_type="predictive_maintenance",
                priority=TaskPriority.MEDIUM,
                status=TaskStatus.PENDING,
                created_at=datetime.now(),
                scheduled_at=scheduled_time or datetime.now() + timedelta(minutes=5),
                parameters={
                    'device_id': device_id,
                    'maintenance_type': maintenance_type,
                    'recommendations': recommendations
                }
            )
            
            await self._queue_task(task)
            
            return {
                'success': True,
                'task_id': task.task_id,
                'scheduled_at': task.scheduled_at,
                'recommendations': recommendations
            }
            
        except Exception as e:
            self.logger.error(f"Error scheduling maintenance task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_ai_insights(self, query: str = None) -> Dict[str, Any]:
        """
        Get AI-powered insights about the network.
        
        Args:
            query: Specific query for insights
            
        Returns:
            AI insights and recommendations
        """
        try:
            insights = {
                'timestamp': datetime.now().isoformat(),
                'network_health': await self._get_network_health_insights(),
                'predictive_maintenance': await self.predictive_engine.get_all_recommendations(),
                'autonomous_detections': await self.detection_engine.get_recent_detections(),
                'task_summary': self._get_task_summary(),
                'recommendations': []
            }
            
            # Generate specific insights based on query
            if query:
                query_insights = await self.nlp_interface.generate_insights(query, insights)
                insights['query_response'] = query_insights
            
            # Generate general recommendations
            insights['recommendations'] = await self._generate_recommendations(insights)
            
            return {
                'success': True,
                'insights': insights
            }
            
        except Exception as e:
            self.logger.error(f"Error generating AI insights: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_task_status(self, task_id: str = None) -> Dict[str, Any]:
        """
        Get status of AI tasks.
        
        Args:
            task_id: Specific task ID, or None for all tasks
            
        Returns:
            Task status information
        """
        try:
            if task_id:
                task = self.active_tasks.get(task_id)
                if not task:
                    # Check task history
                    task = next((t for t in self.task_history if t.task_id == task_id), None)
                
                if not task:
                    return {
                        'success': False,
                        'error': f'Task {task_id} not found'
                    }
                
                return {
                    'success': True,
                    'task': self._task_to_dict(task)
                }
            else:
                return {
                    'success': True,
                    'active_tasks': [self._task_to_dict(task) for task in self.active_tasks.values()],
                    'queued_tasks': [self._task_to_dict(task) for task in self.task_queue],
                    'recent_completed': [self._task_to_dict(task) for task in self.task_history[-10:]]
                }
                
        except Exception as e:
            self.logger.error(f"Error getting task status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler for AI coordination events"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def _coordination_loop(self):
        """Main coordination loop for AI task processing"""
        while self.is_running:
            try:
                # Process queued tasks
                await self._process_task_queue()
                
                # Check for autonomous detections
                await self._check_autonomous_detections()
                
                # Update predictive maintenance
                await self._update_predictive_maintenance()
                
                # Clean up completed tasks
                await self._cleanup_tasks()
                
                # Wait before next iteration
                await asyncio.sleep(self.config.get('coordination_interval', 30))
                
            except Exception as e:
                self.logger.error(f"Error in coordination loop: {e}")
                await asyncio.sleep(5)
    
    async def _queue_task(self, task: AITask):
        """Queue a task for execution"""
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: t.priority.value)
        
        await self._emit_event('task_queued', {'task': self._task_to_dict(task)})
    
    async def _process_task_queue(self):
        """Process tasks in the queue"""
        current_time = datetime.now()
        
        # Find tasks ready for execution
        ready_tasks = [
            task for task in self.task_queue
            if task.status == TaskStatus.PENDING and 
            (task.scheduled_at is None or task.scheduled_at <= current_time)
        ]
        
        for task in ready_tasks[:self.config.get('max_concurrent_tasks', 5)]:
            if len(self.active_tasks) >= self.config.get('max_concurrent_tasks', 5):
                break
                
            # Move task to active
            self.task_queue.remove(task)
            self.active_tasks[task.task_id] = task
            task.status = TaskStatus.RUNNING
            
            # Execute task asynchronously
            asyncio.create_task(self._execute_task(task))
    
    async def _execute_task(self, task: AITask):
        """Execute a specific AI task"""
        try:
            await self._emit_event('task_started', {'task': self._task_to_dict(task)})
            
            result = None
            
            if task.task_type == "nlp_command":
                result = await self._execute_nlp_command(task)
            elif task.task_type == "predictive_maintenance":
                result = await self._execute_maintenance_task(task)
            elif task.task_type == "autonomous_detection":
                result = await self._execute_detection_task(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            # Mark task as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            
            await self._emit_event('task_completed', {
                'task': self._task_to_dict(task),
                'result': result
            })
            
        except Exception as e:
            self.logger.error(f"Error executing task {task.task_id}: {e}")
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = str(e)
            
            await self._emit_event('task_failed', {
                'task': self._task_to_dict(task),
                'error': str(e)
            })
        
        finally:
            # Move task from active to history
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            self.task_history.append(task)
    
    async def _execute_nlp_command(self, task: AITask) -> Dict[str, Any]:
        """Execute a natural language command task"""
        parsed_command = task.parameters['parsed_command']
        
        # Execute the command through the task automation engine
        result = await self.task_engine.execute_command(parsed_command)
        
        return result
    
    async def _execute_maintenance_task(self, task: AITask) -> Dict[str, Any]:
        """Execute a predictive maintenance task"""
        device_id = task.parameters['device_id']
        maintenance_type = task.parameters['maintenance_type']
        
        # Execute maintenance through the predictive engine
        result = await self.predictive_engine.execute_maintenance(device_id, maintenance_type)
        
        return result
    
    async def _execute_detection_task(self, task: AITask) -> Dict[str, Any]:
        """Execute an autonomous detection task"""
        detection_data = task.parameters['detection_data']
        
        # Process the detection through the detection engine
        result = await self.detection_engine.process_detection(detection_data)
        
        return result
    
    async def _check_autonomous_detections(self):
        """Check for new autonomous detections"""
        detections = await self.detection_engine.get_new_detections()
        
        for detection in detections:
            # Create task for each detection
            task = AITask(
                task_id=f"detect_{detection['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description=f"Autonomous detection: {detection['type']}",
                task_type="autonomous_detection",
                priority=TaskPriority.HIGH if detection['severity'] == 'critical' else TaskPriority.MEDIUM,
                status=TaskStatus.PENDING,
                created_at=datetime.now(),
                parameters={'detection_data': detection}
            )
            
            await self._queue_task(task)
    
    async def _update_predictive_maintenance(self):
        """Update predictive maintenance recommendations"""
        await self.predictive_engine.update_recommendations()
    
    async def _cleanup_tasks(self):
        """Clean up old completed tasks"""
        cutoff_time = datetime.now() - timedelta(hours=self.config.get('task_history_hours', 24))
        
        self.task_history = [
            task for task in self.task_history
            if task.completed_at and task.completed_at > cutoff_time
        ]
    
    async def _get_network_health_insights(self) -> Dict[str, Any]:
        """Get AI insights about network health"""
        # This would integrate with the monitoring system
        # For now, return a placeholder
        return {
            'overall_health': 95.5,
            'trending': 'stable',
            'concerns': [],
            'recommendations': []
        }
    
    def _get_task_summary(self) -> Dict[str, Any]:
        """Get summary of AI task activity"""
        return {
            'active_tasks': len(self.active_tasks),
            'queued_tasks': len(self.task_queue),
            'completed_today': len([
                task for task in self.task_history
                if task.completed_at and task.completed_at.date() == datetime.now().date()
            ]),
            'failed_today': len([
                task for task in self.task_history
                if task.status == TaskStatus.FAILED and 
                task.completed_at and task.completed_at.date() == datetime.now().date()
            ])
        }
    
    async def _generate_recommendations(self, insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate AI recommendations based on insights"""
        recommendations = []
        
        # Add predictive maintenance recommendations
        for rec in insights.get('predictive_maintenance', []):
            recommendations.append({
                'type': 'maintenance',
                'priority': rec.get('priority', 'medium'),
                'description': rec.get('description'),
                'action': rec.get('recommended_action')
            })
        
        # Add autonomous detection recommendations
        for detection in insights.get('autonomous_detections', []):
            if detection.get('requires_action'):
                recommendations.append({
                    'type': 'security',
                    'priority': detection.get('severity', 'medium'),
                    'description': detection.get('description'),
                    'action': detection.get('recommended_action')
                })
        
        return recommendations
    
    def _task_to_dict(self, task: AITask) -> Dict[str, Any]:
        """Convert AITask to dictionary"""
        return {
            'task_id': task.task_id,
            'description': task.description,
            'task_type': task.task_type,
            'priority': task.priority.name,
            'status': task.status.value,
            'created_at': task.created_at.isoformat(),
            'scheduled_at': task.scheduled_at.isoformat() if task.scheduled_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'parameters': task.parameters,
            'result': task.result,
            'error': task.error
        }
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to registered handlers"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    await handler(data)
                except Exception as e:
                    self.logger.error(f"Error in event handler for {event_type}: {e}")