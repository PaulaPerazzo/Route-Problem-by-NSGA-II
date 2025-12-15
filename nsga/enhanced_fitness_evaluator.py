"""
Enhanced fitness evaluation with constraint handling for vehicle routing optimization.

This module provides the EnhancedFitnessEvaluator class that integrates constraint checking
with multi-objective fitness evaluation, ensuring solutions are evaluated considering
both objectives and constraint satisfaction.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from nsga.constraint_handler import ConstraintHandler, ConstraintConfig
from nsga.NSGA2 import getNumVehiclesRequired, getRouteCost


class EnhancedFitnessEvaluator:
    """
    Enhanced fitness evaluator that integrates constraint checking with multi-objective optimization.
    
    This class evaluates solutions considering both the dual objectives (vehicle count and cost)
    and constraint satisfaction, applying penalties to infeasible solutions while maintaining
    proper Pareto dominance relationships for feasible solutions.
    """
    
    def __init__(self, constraint_handler: ConstraintHandler):
        """
        Initialize enhanced fitness evaluator.
        
        Args:
            constraint_handler: ConstraintHandler instance for managing constraints
        """
        self.constraint_handler = constraint_handler
        self.logger = logging.getLogger(__name__)
        self.evaluations_count = 0
        self.feasible_evaluations = 0
        self.infeasible_evaluations = 0
    
    def evaluate_constrained_fitness(self, 
                                   individual: List[int], 
                                   instance: Dict[str, Any], 
                                   unit_cost: float = 1.0) -> Tuple[float, float]:
        """
        Evaluate fitness of an individual considering constraints.
        
        This method performs dual objective calculation for feasible solutions
        and applies penalties for infeasible solutions based on the configured
        penalty method.
        
        Args:
            individual: Route sequence representing a solution
            instance: Problem instance data
            unit_cost: Unit cost for transportation
            
        Returns:
            Tuple of (penalized_vehicles, penalized_cost) fitness values
        """
        self.evaluations_count += 1
        
        try:
            # Calculate base fitness values (dual objectives)
            vehicles, cost = self._calculate_dual_objectives(individual, instance, unit_cost)
            
            # Check constraint satisfaction
            is_feasible = self.constraint_handler.validate_solution(individual, instance)
            
            if is_feasible:
                self.feasible_evaluations += 1
                self.logger.debug(f"Feasible solution: vehicles={vehicles}, cost={cost}")
                return (vehicles, cost)
            else:
                self.infeasible_evaluations += 1
                # Apply penalty for constraint violation
                violation_degree = self.constraint_handler.get_violation_degree(individual, instance)
                penalized_fitness = self.constraint_handler.apply_penalty((vehicles, cost), violation_degree)
                
                self.logger.debug(f"Infeasible solution: original=({vehicles}, {cost}), "
                                f"penalized={penalized_fitness}, violation={violation_degree}")
                
                return penalized_fitness
                
        except Exception as e:
            self.logger.error(f"Error evaluating fitness: {e}")
            # Return worst possible fitness for error cases
            return (float('inf'), float('inf'))
    
    def _calculate_dual_objectives(self, 
                                 individual: List[int], 
                                 instance: Dict[str, Any], 
                                 unit_cost: float) -> Tuple[float, float]:
        """
        Calculate the dual objectives: vehicle count and transportation cost.
        
        Args:
            individual: Route sequence representing a solution
            instance: Problem instance data
            unit_cost: Unit cost for transportation
            
        Returns:
            Tuple of (vehicles, cost) representing the two objectives
        """
        vehicles = getNumVehiclesRequired(individual, instance)
        cost = getRouteCost(individual, instance, unit_cost)
        
        return (float(vehicles), float(cost))
    
    def calculate_penalty_factor(self, violation_degree: float) -> float:
        """
        Calculate penalty factor based on violation degree.
        
        This method delegates to the constraint handler but provides
        additional logging and monitoring capabilities.
        
        Args:
            violation_degree: Degree of constraint violation
            
        Returns:
            Penalty factor to apply
        """
        penalty_factor = self.constraint_handler.calculate_penalty_factor(violation_degree)
        self.logger.debug(f"Calculated penalty factor: {penalty_factor} for violation: {violation_degree}")
        return penalty_factor
    
    def is_solution_feasible(self, individual: List[int], instance: Dict[str, Any]) -> bool:
        """
        Check if a solution is feasible without calculating full fitness.
        
        Args:
            individual: Route sequence representing a solution
            instance: Problem instance data
            
        Returns:
            True if solution is feasible, False otherwise
        """
        return self.constraint_handler.validate_solution(individual, instance)
    
    def get_evaluation_statistics(self) -> Dict[str, Any]:
        """
        Get evaluation statistics including feasibility ratios.
        
        Returns:
            Dictionary containing evaluation statistics
        """
        feasibility_ratio = (self.feasible_evaluations / self.evaluations_count 
                           if self.evaluations_count > 0 else 0.0)
        
        stats = {
            'total_evaluations': self.evaluations_count,
            'feasible_evaluations': self.feasible_evaluations,
            'infeasible_evaluations': self.infeasible_evaluations,
            'feasibility_ratio': feasibility_ratio
        }
        
        # Include constraint handler statistics
        constraint_stats = self.constraint_handler.get_statistics()
        stats.update(constraint_stats)
        
        return stats
    
    def reset_statistics(self):
        """Reset evaluation statistics."""
        self.evaluations_count = 0
        self.feasible_evaluations = 0
        self.infeasible_evaluations = 0
        self.constraint_handler.reset_statistics()
    
    def validate_pareto_dominance(self, 
                                solution1: Tuple[float, float], 
                                solution2: Tuple[float, float]) -> Optional[int]:
        """
        Validate Pareto dominance relationship between two solutions.
        
        This method checks dominance considering both objectives simultaneously,
        which is essential for proper multi-objective optimization.
        
        Args:
            solution1: Fitness values (vehicles, cost) for first solution
            solution2: Fitness values (vehicles, cost) for second solution
            
        Returns:
            1 if solution1 dominates solution2
            -1 if solution2 dominates solution1
            0 if solutions are non-dominated
            None if solutions are identical
        """
        vehicles1, cost1 = solution1
        vehicles2, cost2 = solution2
        
        # Check for identical solutions
        if vehicles1 == vehicles2 and cost1 == cost2:
            return None
        
        # Check dominance (minimization objectives)
        dominates_vehicles = vehicles1 <= vehicles2
        dominates_cost = cost1 <= cost2
        strictly_better_vehicles = vehicles1 < vehicles2
        strictly_better_cost = cost1 < cost2
        
        # Solution1 dominates if it's better or equal in all objectives
        # and strictly better in at least one
        if dominates_vehicles and dominates_cost and (strictly_better_vehicles or strictly_better_cost):
            return 1
        
        # Solution2 dominates if it's better or equal in all objectives
        # and strictly better in at least one
        dominates_vehicles_2 = vehicles2 <= vehicles1
        dominates_cost_2 = cost2 <= cost1
        strictly_better_vehicles_2 = vehicles2 < vehicles1
        strictly_better_cost_2 = cost2 < cost1
        
        if dominates_vehicles_2 and dominates_cost_2 and (strictly_better_vehicles_2 or strictly_better_cost_2):
            return -1
        
        # Neither dominates the other
        return 0


def create_enhanced_evaluator(instance: Dict[str, Any], 
                            max_vehicles: Optional[int] = None,
                            penalty_method: str = "static_penalty",
                            penalty_factor: float = 1000.0) -> EnhancedFitnessEvaluator:
    """
    Factory function to create an EnhancedFitnessEvaluator with proper configuration.
    
    Args:
        instance: Problem instance data
        max_vehicles: Maximum vehicles constraint (uses instance data if None)
        penalty_method: Penalty method for constraint violations
        penalty_factor: Base penalty factor
        
    Returns:
        Configured EnhancedFitnessEvaluator instance
    """
    # Determine max vehicles from instance or parameter
    if max_vehicles is None:
        max_vehicles = instance.get('max_vehicle_number', 20)
    
    # Create constraint configuration
    config = ConstraintConfig(
        max_vehicles=max_vehicles,
        penalty_method=penalty_method,
        penalty_factor=penalty_factor
    )
    
    # Create constraint handler
    constraint_handler = ConstraintHandler(config)
    
    # Create and return enhanced evaluator
    return EnhancedFitnessEvaluator(constraint_handler)


def eval_individual_fitness_constrained(individual: List[int], 
                                      instance: Dict[str, Any], 
                                      unit_cost: float,
                                      enhanced_evaluator: EnhancedFitnessEvaluator) -> Tuple[float, float]:
    """
    Enhanced version of eval_individual_fitness that includes constraint validation.
    
    This function serves as a drop-in replacement for the original eval_individual_fitness
    function, adding constraint handling while maintaining the same interface.
    
    Args:
        individual: Route sequence representing a solution
        instance: Problem instance data
        unit_cost: Unit cost for transportation
        enhanced_evaluator: EnhancedFitnessEvaluator instance
        
    Returns:
        Tuple of (vehicles, cost) with penalties applied for infeasible solutions
    """
    return enhanced_evaluator.evaluate_constrained_fitness(individual, instance, unit_cost)