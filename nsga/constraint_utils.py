"""
Utility functions for constraint validation and error handling.

This module provides helper functions for constraint-related operations,
validation utilities, and error handling mechanisms.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from nsga.constraint_handler import ConstraintConfig, ConstraintHandler, ConstraintError


def setup_constraint_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Set up logging for constraint handling operations.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('constraint_handler')
    
    # Avoid adding multiple handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(getattr(logging, log_level.upper()))
    return logger


def validate_population_feasibility(population: List[List[int]], 
                                  instance: Dict[str, Any], 
                                  constraint_handler: ConstraintHandler) -> Tuple[int, int, float]:
    """
    Validate feasibility of an entire population.
    
    Args:
        population: List of individuals (route sequences)
        instance: Problem instance data
        constraint_handler: ConstraintHandler instance
        
    Returns:
        Tuple of (feasible_count, total_count, feasibility_ratio)
    """
    if not population:
        return 0, 0, 0.0
    
    feasible_count = 0
    total_count = len(population)
    
    for individual in population:
        if constraint_handler.validate_solution(individual, instance):
            feasible_count += 1
    
    feasibility_ratio = feasible_count / total_count if total_count > 0 else 0.0
    
    logger = logging.getLogger('constraint_handler')
    logger.info(f"Population feasibility: {feasible_count}/{total_count} ({feasibility_ratio:.2%})")
    
    return feasible_count, total_count, feasibility_ratio


def check_feasibility_threshold(population: List[List[int]], 
                              instance: Dict[str, Any], 
                              constraint_handler: ConstraintHandler) -> bool:
    """
    Check if population meets the feasibility threshold requirement.
    
    Args:
        population: List of individuals (route sequences)
        instance: Problem instance data
        constraint_handler: ConstraintHandler instance
        
    Returns:
        True if feasibility threshold is met, False otherwise
    """
    _, _, feasibility_ratio = validate_population_feasibility(population, instance, constraint_handler)
    threshold_met = feasibility_ratio >= constraint_handler.config.feasibility_threshold
    
    if not threshold_met:
        logger = logging.getLogger('constraint_handler')
        logger.warning(
            f"Feasibility threshold not met: {feasibility_ratio:.2%} < "
            f"{constraint_handler.config.feasibility_threshold:.2%}"
        )
    
    return threshold_met


def log_constraint_violation(individual: List[int], 
                           instance: Dict[str, Any], 
                           violation_degree: float,
                           generation: Optional[int] = None) -> None:
    """
    Log detailed information about a constraint violation.
    
    Args:
        individual: Route sequence that violates constraints
        instance: Problem instance data
        violation_degree: Degree of constraint violation
        generation: Current generation number (optional)
    """
    from nsga.NSGA2 import getNumVehiclesRequired
    
    logger = logging.getLogger('constraint_handler')
    
    try:
        num_vehicles = getNumVehiclesRequired(individual, instance)
        gen_info = f" (Generation {generation})" if generation is not None else ""
        
        logger.warning(
            f"Constraint violation{gen_info}: Solution uses {num_vehicles} vehicles, "
            f"violation degree: {violation_degree}"
        )
        
    except Exception as e:
        logger.error(f"Error logging constraint violation: {e}")


def validate_solution_format(individual: List[int], instance: Dict[str, Any]) -> bool:
    """
    Validate that a solution has the correct format for the given instance.
    
    Args:
        individual: Route sequence to validate
        instance: Problem instance data
        
    Returns:
        True if format is valid, False otherwise
    """
    try:
        # Check if individual is a list
        if not isinstance(individual, list):
            return False
        
        # Check if all elements are integers
        if not all(isinstance(x, int) for x in individual):
            return False
        
        # Check if individual contains the correct number of customers
        expected_customers = instance.get('Number_of_customers', 0)
        if len(individual) != expected_customers:
            return False
        
        # Check if all customer IDs are valid (1 to Number_of_customers)
        expected_ids = set(range(1, expected_customers + 1))
        actual_ids = set(individual)
        if actual_ids != expected_ids:
            return False
        
        return True
        
    except Exception:
        return False


def create_constraint_summary(constraint_handler: ConstraintHandler, 
                            population: List[List[int]], 
                            instance: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a comprehensive summary of constraint handling status.
    
    Args:
        constraint_handler: ConstraintHandler instance
        population: Current population
        instance: Problem instance data
        
    Returns:
        Dictionary containing constraint summary information
    """
    stats = constraint_handler.get_statistics()
    feasible_count, total_count, feasibility_ratio = validate_population_feasibility(
        population, instance, constraint_handler
    )
    
    summary = {
        'constraint_config': constraint_handler.config.to_dict(),
        'population_stats': {
            'total_individuals': total_count,
            'feasible_individuals': feasible_count,
            'feasibility_ratio': feasibility_ratio,
            'threshold_met': feasibility_ratio >= constraint_handler.config.feasibility_threshold
        },
        'violation_stats': stats,
        'constraint_satisfied': feasibility_ratio >= constraint_handler.config.feasibility_threshold
    }
    
    return summary


def handle_constraint_error(error: Exception, context: str = "") -> None:
    """
    Handle constraint-related errors with appropriate logging and re-raising.
    
    Args:
        error: Exception that occurred
        context: Additional context information
        
    Raises:
        ConstraintError: Re-raised with additional context
    """
    logger = logging.getLogger('constraint_handler')
    
    error_msg = f"Constraint error in {context}: {str(error)}" if context else f"Constraint error: {str(error)}"
    logger.error(error_msg)
    
    if isinstance(error, ConstraintError):
        raise error
    else:
        raise ConstraintError(error_msg) from error


def validate_instance_constraints(instance: Dict[str, Any]) -> None:
    """
    Validate that a problem instance contains required constraint information.
    
    Args:
        instance: Problem instance data
        
    Raises:
        ConstraintError: If instance is missing required constraint information
    """
    required_fields = ['Number_of_customers', 'vehicle_capacity']
    
    for field in required_fields:
        if field not in instance:
            raise ConstraintError(f"Instance missing required field: {field}")
    
    # Validate data types
    if not isinstance(instance['Number_of_customers'], int) or instance['Number_of_customers'] <= 0:
        raise ConstraintError("Number_of_customers must be a positive integer")
    
    if not isinstance(instance['vehicle_capacity'], (int, float)) or instance['vehicle_capacity'] <= 0:
        raise ConstraintError("vehicle_capacity must be a positive number")
    
    # Check for customer data
    num_customers = instance['Number_of_customers']
    for i in range(1, num_customers + 1):
        customer_key = f'customer_{i}'
        if customer_key not in instance:
            raise ConstraintError(f"Missing customer data: {customer_key}")


def get_constraint_violation_details(individual: List[int], 
                                   instance: Dict[str, Any], 
                                   constraint_handler: ConstraintHandler) -> Dict[str, Any]:
    """
    Get detailed information about constraint violations for a solution.
    
    Args:
        individual: Route sequence to analyze
        instance: Problem instance data
        constraint_handler: ConstraintHandler instance
        
    Returns:
        Dictionary with detailed violation information
    """
    from nsga.NSGA2 import getNumVehiclesRequired, routeToSubroute
    
    try:
        num_vehicles = getNumVehiclesRequired(individual, instance)
        violation_degree = constraint_handler.get_violation_degree(individual, instance)
        is_feasible = constraint_handler.validate_solution(individual, instance)
        
        details = {
            'is_feasible': is_feasible,
            'vehicles_used': num_vehicles,
            'max_vehicles_allowed': constraint_handler.config.max_vehicles,
            'violation_degree': violation_degree,
            'routes': routeToSubroute(individual, instance) if not is_feasible else None
        }
        
        return details
        
    except Exception as e:
        return {
            'error': str(e),
            'is_feasible': False,
            'violation_degree': float('inf')
        }