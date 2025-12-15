"""
Constraint handling infrastructure for vehicle routing optimization.

This module provides classes and utilities for managing constraints in the VRP system,
including validation, penalty application, and configuration management.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum


class PenaltyMethod(Enum):
    """Enumeration of available penalty methods for constraint violations."""
    DEATH_PENALTY = "death_penalty"
    STATIC_PENALTY = "static_penalty"
    DYNAMIC_PENALTY = "dynamic_penalty"


class ConstraintConfig:
    """
    Configuration class for constraint handling parameters.
    
    Manages constraint settings including maximum vehicles, penalty methods,
    and other constraint-related parameters.
    """
    
    def __init__(self, 
                 max_vehicles: int = 20,
                 penalty_method: str = "static_penalty",
                 penalty_factor: float = 1000.0,
                 repair_attempts: int = 3,
                 feasibility_threshold: float = 0.8):
        """
        Initialize constraint configuration.
        
        Args:
            max_vehicles: Maximum number of vehicles allowed
            penalty_method: Method for applying penalties ("death_penalty", "static_penalty", "dynamic_penalty")
            penalty_factor: Base penalty factor for constraint violations
            repair_attempts: Number of attempts to repair infeasible solutions
            feasibility_threshold: Minimum proportion of feasible solutions to maintain
        
        Raises:
            ValueError: If configuration parameters are invalid
        """
        self.max_vehicles = self._validate_max_vehicles(max_vehicles)
        self.penalty_method = self._validate_penalty_method(penalty_method)
        self.penalty_factor = self._validate_penalty_factor(penalty_factor)
        self.repair_attempts = self._validate_repair_attempts(repair_attempts)
        self.feasibility_threshold = self._validate_feasibility_threshold(feasibility_threshold)
    
    def _validate_max_vehicles(self, max_vehicles: int) -> int:
        """Validate maximum vehicles parameter."""
        if not isinstance(max_vehicles, int) or max_vehicles <= 0:
            raise ValueError(f"max_vehicles must be a positive integer, got {max_vehicles}")
        return max_vehicles
    
    def _validate_penalty_method(self, penalty_method: str) -> PenaltyMethod:
        """Validate penalty method parameter."""
        try:
            return PenaltyMethod(penalty_method)
        except ValueError:
            valid_methods = [method.value for method in PenaltyMethod]
            raise ValueError(f"penalty_method must be one of {valid_methods}, got {penalty_method}")
    
    def _validate_penalty_factor(self, penalty_factor: float) -> float:
        """Validate penalty factor parameter."""
        if not isinstance(penalty_factor, (int, float)) or penalty_factor < 0:
            raise ValueError(f"penalty_factor must be a non-negative number, got {penalty_factor}")
        return float(penalty_factor)
    
    def _validate_repair_attempts(self, repair_attempts: int) -> int:
        """Validate repair attempts parameter."""
        if not isinstance(repair_attempts, int) or repair_attempts < 0:
            raise ValueError(f"repair_attempts must be a non-negative integer, got {repair_attempts}")
        return repair_attempts
    
    def _validate_feasibility_threshold(self, feasibility_threshold: float) -> float:
        """Validate feasibility threshold parameter."""
        if not isinstance(feasibility_threshold, (int, float)) or not (0.0 <= feasibility_threshold <= 1.0):
            raise ValueError(f"feasibility_threshold must be between 0.0 and 1.0, got {feasibility_threshold}")
        return float(feasibility_threshold)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ConstraintConfig':
        """
        Create ConstraintConfig from dictionary.
        
        Args:
            config_dict: Dictionary containing configuration parameters
            
        Returns:
            ConstraintConfig instance
            
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        try:
            return cls(
                max_vehicles=config_dict.get('max_vehicles', 20),
                penalty_method=config_dict.get('penalty_method', 'static_penalty'),
                penalty_factor=config_dict.get('penalty_factor', 1000.0),
                repair_attempts=config_dict.get('repair_attempts', 3),
                feasibility_threshold=config_dict.get('feasibility_threshold', 0.8)
            )
        except (KeyError, TypeError) as e:
            raise ValueError(f"Invalid configuration dictionary: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'max_vehicles': self.max_vehicles,
            'penalty_method': self.penalty_method.value,
            'penalty_factor': self.penalty_factor,
            'repair_attempts': self.repair_attempts,
            'feasibility_threshold': self.feasibility_threshold
        }


class ConstraintHandler:
    """
    Main constraint handling class for vehicle routing optimization.
    
    Provides methods for validating solutions against constraints,
    applying penalties to infeasible solutions, and managing constraint violations.
    """
    
    def __init__(self, config: ConstraintConfig):
        """
        Initialize constraint handler.
        
        Args:
            config: ConstraintConfig instance with constraint parameters
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.violation_count = 0
        self.penalty_applications = 0
    
    def validate_solution(self, individual: List[int], instance: Dict[str, Any]) -> bool:
        """
        Validate if a solution satisfies the vehicle constraint.
        
        Args:
            individual: Route sequence representing a solution
            instance: Problem instance data
            
        Returns:
            True if solution is feasible, False otherwise
        """
        from nsga.NSGA2 import getNumVehiclesRequired
        
        try:
            num_vehicles = getNumVehiclesRequired(individual, instance)
            is_feasible = num_vehicles <= self.config.max_vehicles
            
            if not is_feasible:
                self.violation_count += 1
                self.logger.debug(f"Constraint violation detected: {num_vehicles} vehicles > {self.config.max_vehicles} limit")
            
            return is_feasible
            
        except Exception as e:
            self.logger.error(f"Error validating solution: {e}")
            return False
    
    def get_violation_degree(self, individual: List[int], instance: Dict[str, Any]) -> float:
        """
        Calculate the degree of constraint violation.
        
        Args:
            individual: Route sequence representing a solution
            instance: Problem instance data
            
        Returns:
            Violation degree (0.0 if feasible, positive value if infeasible)
        """
        from nsga.NSGA2 import getNumVehiclesRequired
        
        try:
            num_vehicles = getNumVehiclesRequired(individual, instance)
            violation = max(0, num_vehicles - self.config.max_vehicles)
            return float(violation)
            
        except Exception as e:
            self.logger.error(f"Error calculating violation degree: {e}")
            return float('inf')  # Return infinite penalty for errors
    
    def apply_penalty(self, fitness_values: Tuple[float, float], violation_degree: float) -> Tuple[float, float]:
        """
        Apply penalty to fitness values based on constraint violation.
        
        Args:
            fitness_values: Original fitness values (vehicles, cost)
            violation_degree: Degree of constraint violation
            
        Returns:
            Modified fitness values with penalty applied
        """
        if violation_degree <= 0:
            return fitness_values  # No penalty for feasible solutions
        
        vehicles, cost = fitness_values
        penalty_factor = self.calculate_penalty_factor(violation_degree)
        
        if self.config.penalty_method == PenaltyMethod.DEATH_PENALTY:
            # Death penalty: make solution extremely unfit
            penalized_fitness = (float('inf'), float('inf'))
        elif self.config.penalty_method == PenaltyMethod.STATIC_PENALTY:
            # Static penalty: add fixed penalty based on violation
            penalty = self.config.penalty_factor * violation_degree
            penalized_fitness = (vehicles + penalty, cost + penalty)
        elif self.config.penalty_method == PenaltyMethod.DYNAMIC_PENALTY:
            # Dynamic penalty: penalty increases with generation (simplified version)
            penalty = penalty_factor * violation_degree
            penalized_fitness = (vehicles + penalty, cost + penalty)
        else:
            # Fallback to static penalty
            penalty = self.config.penalty_factor * violation_degree
            penalized_fitness = (vehicles + penalty, cost + penalty)
        
        self.penalty_applications += 1
        self.logger.debug(f"Applied penalty: violation={violation_degree}, penalty_factor={penalty_factor}")
        
        return penalized_fitness
    
    def calculate_penalty_factor(self, violation_degree: float) -> float:
        """
        Calculate penalty factor based on violation degree and method.
        
        Args:
            violation_degree: Degree of constraint violation
            
        Returns:
            Penalty factor to apply
        """
        base_factor = self.config.penalty_factor
        
        if self.config.penalty_method == PenaltyMethod.DYNAMIC_PENALTY:
            # For dynamic penalty, increase factor based on violation severity
            return base_factor * (1.0 + violation_degree)
        else:
            return base_factor
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get constraint handling statistics.
        
        Returns:
            Dictionary with violation and penalty statistics
        """
        return {
            'violation_count': self.violation_count,
            'penalty_applications': self.penalty_applications
        }
    
    def reset_statistics(self):
        """Reset constraint handling statistics."""
        self.violation_count = 0
        self.penalty_applications = 0


class ConstraintError(Exception):
    """Exception raised for constraint-related errors."""
    pass


def load_constraint_config_from_json(json_data: Dict[str, Any]) -> ConstraintConfig:
    """
    Load constraint configuration from JSON instance data.
    
    Args:
        json_data: JSON instance data containing constraint parameters
        
    Returns:
        ConstraintConfig instance
        
    Raises:
        ConstraintError: If configuration cannot be loaded
    """
    try:
        # Extract max vehicles from instance data, default to 20 if not present
        max_vehicles = json_data.get('max_vehicle_number', 20)
        
        # Create configuration with default values for other parameters
        config = ConstraintConfig(max_vehicles=max_vehicles)
        
        logging.getLogger(__name__).info(f"Loaded constraint config: max_vehicles={max_vehicles}")
        return config
        
    except Exception as e:
        raise ConstraintError(f"Failed to load constraint configuration: {e}")


def validate_constraint_parameters(max_vehicles: int, penalty_method: str, penalty_factor: float) -> None:
    """
    Validate constraint parameters from command line or configuration.
    
    Args:
        max_vehicles: Maximum number of vehicles
        penalty_method: Penalty method name
        penalty_factor: Penalty factor value
        
    Raises:
        ConstraintError: If parameters are invalid
    """
    try:
        # Validate by creating a temporary config
        ConstraintConfig(
            max_vehicles=max_vehicles,
            penalty_method=penalty_method,
            penalty_factor=penalty_factor
        )
    except ValueError as e:
        raise ConstraintError(f"Invalid constraint parameters: {e}")