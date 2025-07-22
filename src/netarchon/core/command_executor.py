"""
NetArchon Command Execution Module

Framework for executing commands on network devices with proper error handling.
"""

import socket
import time
from datetime import datetime
from typing import List, Optional

from ..models.connection import ConnectionInfo, CommandResult
from ..utils.exceptions import CommandExecutionError, TimeoutError
from ..utils.logger import get_logger


class CommandExecutor:
    """Main command execution logic for network devices."""
    
    def __init__(self, default_timeout: int = 30):
        """Initialize command executor.
        
        Args:
            default_timeout: Default command timeout in seconds
        """
        self.default_timeout = default_timeout
        self.logger = get_logger(f"{__name__}.CommandExecutor")
    
    def execute_command(self, 
                       connection: ConnectionInfo, 
                       command: str, 
                       timeout: Optional[int] = None) -> CommandResult:
        """Execute a single command on a network device.
        
        Args:
            connection: Active connection to the device
            command: Command to execute
            timeout: Command timeout in seconds (uses default if None)
            
        Returns:
            CommandResult with execution details
            
        Raises:
            CommandExecutionError: If command execution fails
            TimeoutError: If command execution times out
        """
        if timeout is None:
            timeout = self.default_timeout
            
        self.logger.info(f"Executing command: {command}", 
                        device_id=connection.device_id, 
                        command=command,
                        timeout=timeout)
        
        if not hasattr(connection, '_ssh_client') or not connection._ssh_client:
            raise CommandExecutionError(f"No active SSH connection for device {connection.device_id}",
                                      {"device_id": connection.device_id})
        
        start_time = time.time()
        
        try:
            # Execute command via SSH
            stdin, stdout, stderr = connection._ssh_client.exec_command(
                command, timeout=timeout
            )
            
            # Read output and error streams
            output = stdout.read().decode('utf-8', errors='replace')
            error = stderr.read().decode('utf-8', errors='replace')
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Determine success based on exit status
            exit_status = stdout.channel.recv_exit_status()
            success = exit_status == 0
            
            # Update connection activity
            connection.update_activity()
            
            result = CommandResult(
                success=success,
                output=output,
                error=error,
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                command=command,
                device_id=connection.device_id
            )
            
            if success:
                self.logger.debug(f"Command executed successfully",
                                device_id=connection.device_id,
                                command=command,
                                execution_time=execution_time)
            else:
                self.logger.warning(f"Command failed with exit status {exit_status}",
                                  device_id=connection.device_id,
                                  command=command,
                                  exit_status=exit_status,
                                  error=error)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Handle timeout specifically
            if "timeout" in str(e).lower():
                self.logger.error(f"Command timed out after {timeout} seconds",
                                device_id=connection.device_id,
                                command=command,
                                timeout=timeout)
                
                raise TimeoutError(f"Command '{command}' timed out after {timeout} seconds",
                                 {"device_id": connection.device_id, 
                                  "command": command, 
                                  "timeout": timeout})
            
            # Handle other execution errors
            self.logger.error(f"Command execution failed: {str(e)}",
                            device_id=connection.device_id,
                            command=command,
                            error=str(e),
                            execution_time=execution_time)
            
            # Return failed result instead of raising exception for non-timeout errors
            return CommandResult(
                success=False,
                output="",
                error=str(e),
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                command=command,
                device_id=connection.device_id
            )
    
    def execute_with_privilege(self, 
                              connection: ConnectionInfo, 
                              command: str, 
                              enable_password: str,
                              timeout: Optional[int] = None) -> CommandResult:
        """Execute command with privilege escalation (enable mode).
        
        Args:
            connection: Active connection to the device
            command: Command to execute in privileged mode
            enable_password: Password for privilege escalation
            timeout: Command timeout in seconds
            
        Returns:
            CommandResult with execution details
            
        Raises:
            CommandExecutionError: If privilege escalation or command execution fails
        """
        if timeout is None:
            timeout = self.default_timeout
            
        self.logger.info(f"Executing privileged command: {command}", 
                        device_id=connection.device_id, 
                        command=command)
        
        if not hasattr(connection, '_ssh_client') or not connection._ssh_client:
            raise CommandExecutionError(f"No active SSH connection for device {connection.device_id}",
                                      {"device_id": connection.device_id})
        
        start_time = time.time()
        
        try:
            # Create interactive shell for privilege escalation
            shell = connection._ssh_client.invoke_shell()
            shell.settimeout(timeout)
            
            # Wait for initial prompt
            time.sleep(0.5)
            initial_output = shell.recv(1024).decode('utf-8', errors='replace')
            
            # Enter enable mode
            shell.send('enable\n')
            time.sleep(0.5)
            
            # Check if password prompt appeared
            prompt_output = shell.recv(1024).decode('utf-8', errors='replace')
            if 'password' in prompt_output.lower() or ':' in prompt_output:
                shell.send(f'{enable_password}\n')
                time.sleep(0.5)
                
                # Check for successful privilege escalation
                enable_result = shell.recv(1024).decode('utf-8', errors='replace')
                if 'denied' in enable_result.lower() or 'invalid' in enable_result.lower():
                    raise CommandExecutionError("Privilege escalation failed - invalid enable password",
                                              {"device_id": connection.device_id})
            
            # Execute the actual command
            shell.send(f'{command}\n')
            time.sleep(0.5)
            
            # Collect output
            output_parts = []
            while True:
                try:
                    chunk = shell.recv(1024).decode('utf-8', errors='replace')
                    if not chunk:
                        break
                    output_parts.append(chunk)
                    
                    # Check for command completion (basic prompt detection)
                    if '#' in chunk or '>' in chunk:
                        # Wait a bit more to ensure we got all output
                        time.sleep(0.2)
                        try:
                            final_chunk = shell.recv(1024).decode('utf-8', errors='replace')
                            if final_chunk:
                                output_parts.append(final_chunk)
                        except:
                            pass
                        break
                        
                except socket.timeout:
                    break
            
            # Exit enable mode
            shell.send('exit\n')
            shell.close()
            
            # Process output
            full_output = ''.join(output_parts)
            
            # Clean up output (remove command echo and prompts)
            lines = full_output.split('\n')
            cleaned_lines = []
            skip_next = False
            
            for line in lines:
                if skip_next:
                    skip_next = False
                    continue
                    
                # Skip command echo
                if command in line:
                    skip_next = True
                    continue
                    
                # Skip prompts and enable commands
                if line.strip().endswith('#') or line.strip().endswith('>'):
                    continue
                if 'enable' in line and len(line.strip()) < 10:
                    continue
                    
                cleaned_lines.append(line)
            
            cleaned_output = '\n'.join(cleaned_lines).strip()
            execution_time = time.time() - start_time
            
            # Update connection activity
            connection.update_activity()
            
            result = CommandResult(
                success=True,
                output=cleaned_output,
                error="",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                command=command,
                device_id=connection.device_id
            )
            
            self.logger.info(f"Privileged command executed successfully",
                           device_id=connection.device_id,
                           command=command,
                           execution_time=execution_time)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            self.logger.error(f"Privileged command execution failed: {str(e)}",
                            device_id=connection.device_id,
                            command=command,
                            error=str(e),
                            execution_time=execution_time)
            
            return CommandResult(
                success=False,
                output="",
                error=f"Privileged execution failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                command=command,
                device_id=connection.device_id
            )

    def execute_commands(self, 
                        connection: ConnectionInfo, 
                        commands: List[str],
                        timeout: Optional[int] = None,
                        stop_on_error: bool = False) -> List[CommandResult]:
        """Execute multiple commands sequentially.
        
        Args:
            connection: Active connection to the device
            commands: List of commands to execute
            timeout: Command timeout in seconds (uses default if None)
            stop_on_error: Whether to stop execution on first error
            
        Returns:
            List of CommandResult objects
        """
        self.logger.info(f"Executing {len(commands)} commands",
                        device_id=connection.device_id,
                        command_count=len(commands),
                        stop_on_error=stop_on_error)
        
        results = []
        
        for i, command in enumerate(commands):
            try:
                result = self.execute_command(connection, command, timeout)
                results.append(result)
                
                # Check if we should stop on error
                if stop_on_error and result.has_error():
                    self.logger.warning(f"Stopping command execution due to error in command {i+1}",
                                      device_id=connection.device_id,
                                      failed_command=command,
                                      executed_commands=i+1,
                                      total_commands=len(commands))
                    break
                    
            except Exception as e:
                # Create error result
                error_result = CommandResult(
                    success=False,
                    output="",
                    error=str(e),
                    execution_time=0.0,
                    timestamp=datetime.utcnow(),
                    command=command,
                    device_id=connection.device_id
                )
                results.append(error_result)
                
                if stop_on_error:
                    self.logger.error(f"Stopping command execution due to exception in command {i+1}",
                                    device_id=connection.device_id,
                                    failed_command=command,
                                    error=str(e))
                    break
        
        self.logger.info(f"Completed execution of {len(results)} commands",
                        device_id=connection.device_id,
                        successful_commands=sum(1 for r in results if r.success),
                        failed_commands=sum(1 for r in results if not r.success))
        
        return results


class CommandParser:
    """Parses and validates commands before execution."""
    
    def __init__(self):
        """Initialize command parser."""
        self.logger = get_logger(f"{__name__}.CommandParser")
        
        # Define potentially dangerous commands
        self.dangerous_commands = {
            'reload', 'reboot', 'shutdown', 'erase', 'format', 'delete',
            'clear', 'reset', 'factory-reset', 'write erase'
        }
    
    def validate_command(self, command: str) -> bool:
        """Validate command for safety and syntax.
        
        Args:
            command: Command to validate
            
        Returns:
            True if command is valid and safe, False otherwise
        """
        if not command or not command.strip():
            self.logger.warning("Empty or whitespace-only command rejected")
            return False
        
        command_lower = command.lower().strip()
        
        # Check for dangerous commands
        for dangerous in self.dangerous_commands:
            if dangerous in command_lower:
                self.logger.warning(f"Potentially dangerous command rejected: {command}",
                                  dangerous_pattern=dangerous)
                return False
        
        # Basic syntax validation
        if len(command) > 1000:  # Arbitrary length limit
            self.logger.warning(f"Command too long (>{1000} chars): {len(command)} chars")
            return False
        
        # Check for suspicious patterns
        suspicious_patterns = ['rm -rf', 'dd if=', '> /dev/', 'mkfs']
        for pattern in suspicious_patterns:
            if pattern in command_lower:
                self.logger.warning(f"Suspicious command pattern rejected: {command}",
                                  pattern=pattern)
                return False
        
        return True
    
    def sanitize_command(self, command: str) -> str:
        """Sanitize command by removing potentially harmful elements.
        
        Args:
            command: Command to sanitize
            
        Returns:
            Sanitized command string
        """
        if not command:
            return ""
        
        # Remove leading/trailing whitespace
        sanitized = command.strip()
        
        # Remove multiple consecutive spaces
        import re
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Remove null bytes and other control characters
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\t\n')
        
        self.logger.debug(f"Command sanitized",
                         original_length=len(command),
                         sanitized_length=len(sanitized))
        
        return sanitized


class ResponseProcessor:
    """Processes command responses and extracts useful information."""
    
    def __init__(self):
        """Initialize response processor."""
        self.logger = get_logger(f"{__name__}.ResponseProcessor")
    
    def process_response(self, result: CommandResult) -> CommandResult:
        """Process command response and enhance result with parsed data.
        
        Args:
            result: Raw command result
            
        Returns:
            Enhanced CommandResult with processed information
        """
        if not result.success or not result.output:
            return result
        
        # Clean up output
        cleaned_output = self._clean_output(result.output)
        
        # Create enhanced result
        enhanced_result = CommandResult(
            success=result.success,
            output=cleaned_output,
            error=result.error,
            execution_time=result.execution_time,
            timestamp=result.timestamp,
            command=result.command,
            device_id=result.device_id
        )
        
        # Add metadata based on command type
        if not hasattr(enhanced_result, 'additional_data'):
            enhanced_result.additional_data = {}
        
        enhanced_result.additional_data.update(
            self._extract_metadata(result.command, cleaned_output)
        )
        
        return enhanced_result
    
    def _clean_output(self, output: str) -> str:
        """Clean command output by removing control characters and formatting.
        
        Args:
            output: Raw command output
            
        Returns:
            Cleaned output string
        """
        if not output:
            return ""
        
        import re
        
        # Remove ANSI escape sequences
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', output)
        
        # Remove carriage returns
        cleaned = cleaned.replace('\r', '')
        
        # Remove excessive blank lines
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
        
        # Strip leading/trailing whitespace
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _extract_metadata(self, command: str, output: str) -> dict:
        """Extract metadata from command output based on command type.
        
        Args:
            command: Executed command
            output: Command output
            
        Returns:
            Dictionary with extracted metadata
        """
        metadata = {}
        command_lower = command.lower()
        
        # Extract line count
        metadata['output_lines'] = len(output.split('\n')) if output else 0
        
        # Command-specific metadata extraction
        if 'show version' in command_lower:
            metadata['command_type'] = 'version_info'
        elif 'show interface' in command_lower:
            metadata['command_type'] = 'interface_info'
        elif 'show ip route' in command_lower or 'show route' in command_lower:
            metadata['command_type'] = 'routing_info'
        elif 'show running-config' in command_lower or 'show configuration' in command_lower:
            metadata['command_type'] = 'configuration'
        else:
            metadata['command_type'] = 'general'
        
        return metadata