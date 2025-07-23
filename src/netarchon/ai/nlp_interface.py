"""
Natural Language Processing Interface for NetArchon

Provides natural language understanding and generation capabilities
for network management commands and queries.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

# For local AI model integration (Ollama)
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# For advanced NLP processing
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


@dataclass
class ParsedCommand:
    """Parsed natural language command"""
    intent: str
    entities: Dict[str, Any]
    confidence: float
    parameters: Dict[str, Any]
    valid: bool
    suggestion: Optional[str] = None


class NaturalLanguageInterface:
    """
    Natural language processing interface for network management.
    
    Supports both local AI models (Ollama) and rule-based processing
    for parsing commands and generating responses.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the NLP interface.
        
        Args:
            config: NLP configuration parameters
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Model configuration
        self.use_local_model = self.config.get('use_local_model', True) and OLLAMA_AVAILABLE
        self.model_name = self.config.get('model_name', 'llama3.1:8b')
        
        # Command patterns for rule-based processing
        self.command_patterns = self._initialize_command_patterns()
        
        # Entity extraction patterns
        self.entity_patterns = self._initialize_entity_patterns()
        
        # Intent classification
        self.intent_keywords = self._initialize_intent_keywords()
        
        # NLP model
        self.nlp_model = None
        
    async def initialize(self):
        """Initialize the NLP interface"""
        self.logger.info("Initializing Natural Language Interface...")
        
        if self.use_local_model:
            try:
                # Test Ollama connection
                models = ollama.list()
                if self.model_name not in [m['name'] for m in models['models']]:
                    self.logger.warning(f"Model {self.model_name} not found, falling back to rule-based processing")
                    self.use_local_model = False
                else:
                    self.logger.info(f"Using local AI model: {self.model_name}")
            except Exception as e:
                self.logger.warning(f"Failed to connect to Ollama: {e}, falling back to rule-based processing")
                self.use_local_model = False
        
        # Load spaCy model if available
        if SPACY_AVAILABLE:
            try:
                self.nlp_model = spacy.load("en_core_web_sm")
                self.logger.info("Loaded spaCy NLP model")
            except OSError:
                self.logger.warning("spaCy model not found, using basic NLP processing")
        
        self.logger.info("Natural Language Interface initialized")
    
    async def parse_command(self, command: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Parse a natural language command into structured format.
        
        Args:
            command: Natural language command
            context: Additional context for parsing
            
        Returns:
            Parsed command structure
        """
        try:
            command = command.strip().lower()
            
            if self.use_local_model:
                return await self._parse_with_ai_model(command, context)
            else:
                return await self._parse_with_rules(command, context)
                
        except Exception as e:
            self.logger.error(f"Error parsing command: {e}")
            return {
                'valid': False,
                'error': str(e),
                'suggestion': 'Please try rephrasing your command'
            }
    
    async def generate_insights(self, query: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI insights based on a query and network data.
        
        Args:
            query: User query for insights
            data: Network data for analysis
            
        Returns:
            Generated insights
        """
        try:
            if self.use_local_model:
                return await self._generate_insights_with_ai(query, data)
            else:
                return await self._generate_insights_with_rules(query, data)
                
        except Exception as e:
            self.logger.error(f"Error generating insights: {e}")
            return {
                'error': str(e),
                'insights': 'Unable to generate insights at this time'
            }
    
    async def _parse_with_ai_model(self, command: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Parse command using local AI model"""
        try:
            # Create prompt for command parsing
            prompt = self._create_parsing_prompt(command, context)
            
            # Query the AI model
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    'temperature': 0.1,  # Low temperature for consistent parsing
                    'top_p': 0.9
                }
            )
            
            # Parse the AI response
            parsed_result = self._parse_ai_response(response['response'])
            
            # Validate and enhance the result
            return self._validate_parsed_command(parsed_result, command)
            
        except Exception as e:
            self.logger.error(f"Error parsing with AI model: {e}")
            # Fall back to rule-based parsing
            return await self._parse_with_rules(command, context)
    
    async def _parse_with_rules(self, command: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Parse command using rule-based approach"""
        # Extract intent
        intent = self._extract_intent(command)
        
        # Extract entities
        entities = self._extract_entities(command)
        
        # Extract parameters based on intent
        parameters = self._extract_parameters(command, intent, entities)
        
        # Calculate confidence
        confidence = self._calculate_confidence(command, intent, entities)
        
        # Validate command
        valid = confidence > 0.6 and intent != 'unknown'
        
        result = {
            'intent': intent,
            'entities': entities,
            'parameters': parameters,
            'confidence': confidence,
            'valid': valid
        }
        
        if not valid:
            result['suggestion'] = self._generate_suggestion(command, intent)
        
        return result
    
    async def _generate_insights_with_ai(self, query: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights using AI model"""
        try:
            # Create prompt for insight generation
            prompt = self._create_insights_prompt(query, data)
            
            # Query the AI model
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    'temperature': 0.3,  # Moderate temperature for creative insights
                    'top_p': 0.9
                }
            )
            
            return {
                'insights': response['response'],
                'confidence': 0.8,  # AI-generated insights have high confidence
                'source': 'ai_model'
            }
            
        except Exception as e:
            self.logger.error(f"Error generating insights with AI: {e}")
            return await self._generate_insights_with_rules(query, data)
    
    async def _generate_insights_with_rules(self, query: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights using rule-based approach"""
        insights = []
        
        # Analyze network health
        if 'network_health' in data:
            health = data['network_health']
            if health.get('overall_health', 0) < 90:
                insights.append(f"Network health is at {health.get('overall_health', 0)}%, which is below optimal.")
        
        # Analyze predictive maintenance
        if 'predictive_maintenance' in data:
            maintenance_items = data['predictive_maintenance']
            if maintenance_items:
                insights.append(f"There are {len(maintenance_items)} predictive maintenance recommendations.")
        
        # Analyze autonomous detections
        if 'autonomous_detections' in data:
            detections = data['autonomous_detections']
            critical_detections = [d for d in detections if d.get('severity') == 'critical']
            if critical_detections:
                insights.append(f"Found {len(critical_detections)} critical security detections requiring attention.")
        
        # Analyze task summary
        if 'task_summary' in data:
            tasks = data['task_summary']
            if tasks.get('failed_today', 0) > 0:
                insights.append(f"{tasks['failed_today']} tasks failed today, requiring investigation.")
        
        return {
            'insights': ' '.join(insights) if insights else 'Network appears to be operating normally.',
            'confidence': 0.7,
            'source': 'rule_based'
        }
    
    def _initialize_command_patterns(self) -> Dict[str, List[str]]:
        """Initialize command patterns for rule-based parsing"""
        return {
            'status': [
                r'(show|get|check|what is|what\'s) (the )?status (of|for) (.+)',
                r'(how is|how\'s) (.+) (doing|performing)',
                r'is (.+) (online|offline|working|up|down)',
                r'status (.+)'
            ],
            'restart': [
                r'restart (.+)',
                r'reboot (.+)',
                r'bounce (.+)',
                r'cycle (.+)'
            ],
            'monitor': [
                r'monitor (.+)',
                r'watch (.+)',
                r'track (.+)',
                r'observe (.+)'
            ],
            'alert': [
                r'(create|set up|add) (an )?alert (for|on) (.+)',
                r'notify me (when|if) (.+)',
                r'alert (me|us) (when|if) (.+)'
            ],
            'metrics': [
                r'(show|get|display) (the )?metrics (for|of) (.+)',
                r'what are the metrics (for|of) (.+)',
                r'metrics (.+)'
            ],
            'troubleshoot': [
                r'troubleshoot (.+)',
                r'diagnose (.+)',
                r'fix (.+)',
                r'resolve (.+)',
                r'what\'s wrong with (.+)'
            ],
            'configure': [
                r'configure (.+)',
                r'set up (.+)',
                r'change (.+) settings',
                r'modify (.+) configuration'
            ]
        }
    
    def _initialize_entity_patterns(self) -> Dict[str, str]:
        """Initialize entity extraction patterns"""
        return {
            'device': r'(xfinity gateway|arris modem|arris s33|netgear router|netgear orbi|mini pc|server|gateway|modem|router|switch|access point)',
            'metric': r'(cpu usage|memory usage|disk usage|bandwidth|latency|uptime|temperature|power|signal strength|snr)',
            'time': r'(last hour|last day|last week|yesterday|today|now|currently)',
            'threshold': r'(\d+)%?',
            'ip_address': r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
            'service': r'(ssh|http|https|ftp|dns|dhcp|ntp)'
        }
    
    def _initialize_intent_keywords(self) -> Dict[str, List[str]]:
        """Initialize intent classification keywords"""
        return {
            'status': ['status', 'check', 'show', 'display', 'get', 'how', 'is', 'are'],
            'restart': ['restart', 'reboot', 'bounce', 'cycle', 'reset'],
            'monitor': ['monitor', 'watch', 'track', 'observe', 'follow'],
            'alert': ['alert', 'notify', 'warn', 'tell', 'inform'],
            'metrics': ['metrics', 'stats', 'statistics', 'data', 'performance'],
            'troubleshoot': ['troubleshoot', 'diagnose', 'fix', 'resolve', 'problem', 'issue', 'wrong'],
            'configure': ['configure', 'setup', 'set', 'change', 'modify', 'update']
        }
    
    def _extract_intent(self, command: str) -> str:
        """Extract intent from command"""
        # Check patterns first
        for intent, patterns in self.command_patterns.items():
            for pattern in patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return intent
        
        # Check keywords
        words = command.lower().split()
        intent_scores = {}
        
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for word in words if word in keywords)
            if score > 0:
                intent_scores[intent] = score
        
        if intent_scores:
            return max(intent_scores, key=intent_scores.get)
        
        return 'unknown'
    
    def _extract_entities(self, command: str) -> Dict[str, Any]:
        """Extract entities from command"""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, command, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches[0] if len(matches) == 1 else matches
        
        # Use spaCy for additional entity extraction if available
        if self.nlp_model:
            doc = self.nlp_model(command)
            for ent in doc.ents:
                if ent.label_ in ['ORG', 'PRODUCT', 'GPE']:
                    entities['named_entity'] = entities.get('named_entity', [])
                    if isinstance(entities['named_entity'], str):
                        entities['named_entity'] = [entities['named_entity']]
                    entities['named_entity'].append(ent.text)
        
        return entities
    
    def _extract_parameters(self, command: str, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters based on intent and entities"""
        parameters = {}
        
        if intent == 'status':
            parameters['target'] = entities.get('device', 'network')
            parameters['include_metrics'] = 'metric' in entities
        
        elif intent == 'restart':
            parameters['target'] = entities.get('device')
            parameters['force'] = 'force' in command.lower()
        
        elif intent == 'monitor':
            parameters['target'] = entities.get('device', 'network')
            parameters['duration'] = entities.get('time', '1 hour')
            parameters['metrics'] = entities.get('metric', ['all'])
        
        elif intent == 'alert':
            parameters['target'] = entities.get('device')
            parameters['metric'] = entities.get('metric')
            parameters['threshold'] = entities.get('threshold')
        
        elif intent == 'metrics':
            parameters['target'] = entities.get('device', 'network')
            parameters['time_range'] = entities.get('time', 'last hour')
            parameters['specific_metrics'] = entities.get('metric')
        
        elif intent == 'troubleshoot':
            parameters['target'] = entities.get('device')
            parameters['auto_fix'] = 'fix' in command.lower()
        
        elif intent == 'configure':
            parameters['target'] = entities.get('device')
            parameters['service'] = entities.get('service')
        
        return parameters
    
    def _calculate_confidence(self, command: str, intent: str, entities: Dict[str, Any]) -> float:
        """Calculate confidence score for parsed command"""
        confidence = 0.0
        
        # Base confidence for recognized intent
        if intent != 'unknown':
            confidence += 0.4
        
        # Boost for pattern matches
        if intent in self.command_patterns:
            for pattern in self.command_patterns[intent]:
                if re.search(pattern, command, re.IGNORECASE):
                    confidence += 0.3
                    break
        
        # Boost for recognized entities
        confidence += min(len(entities) * 0.1, 0.3)
        
        # Penalty for very short commands
        if len(command.split()) < 3:
            confidence -= 0.1
        
        return min(max(confidence, 0.0), 1.0)
    
    def _generate_suggestion(self, command: str, intent: str) -> str:
        """Generate suggestion for invalid commands"""
        if intent == 'unknown':
            return "Try commands like 'show status of router' or 'restart gateway'"
        
        suggestions = {
            'status': "Try 'show status of [device]' or 'how is the network doing'",
            'restart': "Try 'restart [device]' or 'reboot gateway'",
            'monitor': "Try 'monitor [device]' or 'watch network performance'",
            'alert': "Try 'alert me when CPU usage exceeds 80%'",
            'metrics': "Try 'show metrics for router' or 'get network statistics'",
            'troubleshoot': "Try 'troubleshoot [device]' or 'diagnose network issues'",
            'configure': "Try 'configure [device]' or 'set up alerts'"
        }
        
        return suggestions.get(intent, "Please rephrase your command")
    
    def _create_parsing_prompt(self, command: str, context: Dict[str, Any] = None) -> str:
        """Create prompt for AI model command parsing"""
        context_str = ""
        if context:
            context_str = f"\\nContext: {json.dumps(context, indent=2)}"
        
        return f\"\"\"You are a network management AI assistant. Parse the following natural language command into a structured format.
        
Command: "{command}"{context_str}

Please respond with a JSON object containing:
- intent: The main action (status, restart, monitor, alert, metrics, troubleshoot, configure)
- entities: Extracted entities like devices, metrics, thresholds, etc.
- parameters: Specific parameters for the command
- confidence: Confidence score (0.0 to 1.0)
- valid: Whether the command is valid and executable

Available devices: xfinity gateway, arris s33 modem, netgear orbi router, mini pc server
Available metrics: cpu usage, memory usage, disk usage, bandwidth, latency, uptime

Response (JSON only):\"\"\"
    
    def _create_insights_prompt(self, query: str, data: Dict[str, Any]) -> str:
        """Create prompt for AI model insight generation"""
        data_str = json.dumps(data, indent=2, default=str)
        
        return f\"\"\"You are a network management AI assistant. Analyze the following network data and provide insights based on the user's query.

Query: "{query}"

Network Data:
{data_str}

Please provide:
1. Key insights about the network status
2. Any issues or concerns identified
3. Recommendations for improvement
4. Answers to the specific query

Response:\"\"\"
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse AI model response into structured format"""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\\{.*\\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # If no JSON found, create a basic structure
                return {
                    'intent': 'unknown',
                    'entities': {},
                    'parameters': {},
                    'confidence': 0.3,
                    'valid': False,
                    'raw_response': response
                }
        except json.JSONDecodeError:
            return {
                'intent': 'unknown',
                'entities': {},
                'parameters': {},
                'confidence': 0.2,
                'valid': False,
                'error': 'Failed to parse AI response'
            }
    
    def _validate_parsed_command(self, parsed: Dict[str, Any], original_command: str) -> Dict[str, Any]:
        """Validate and enhance parsed command"""
        # Ensure required fields exist
        parsed.setdefault('intent', 'unknown')
        parsed.setdefault('entities', {})
        parsed.setdefault('parameters', {})
        parsed.setdefault('confidence', 0.5)
        parsed.setdefault('valid', False)
        
        # Validate intent
        valid_intents = ['status', 'restart', 'monitor', 'alert', 'metrics', 'troubleshoot', 'configure']
        if parsed['intent'] not in valid_intents:
            parsed['intent'] = 'unknown'
            parsed['valid'] = False
        
        # Adjust confidence based on validation
        if not parsed['valid'] and parsed['confidence'] > 0.6:
            parsed['confidence'] = 0.5
        
        # Add original command for reference
        parsed['original_command'] = original_command
        
        return parsed