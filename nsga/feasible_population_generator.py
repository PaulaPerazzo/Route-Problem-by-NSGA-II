"""
Feasible population generation for constrained vehicle routing optimization.

This module provides the FeasiblePopulationGenerator class that creates initial populations
respecting vehicle constraints, implements solution repair mechanisms, and handles
regeneration logic for infeasible solutions.
"""

import random
import logging
from typing import List, Dict, Any, Optional, Tuple
from nsga.constraint_handler import ConstraintHandler, ConstraintConfig
from nsga.NSGA2 import getNumVehiclesRequired, routeToSubroute


class FeasiblePopulationGenerator:
    """
    Generator for creating feasible initial populations and repairing constraint violations.
    
    This class implements constraint-aware individual generation methods, solution repair
    mechanisms, and regeneration logic to ensure all generated solutions respect the
    maximum vehicle constraint while maintaining solution diversity.
    """
    
    def __init__(self, constraint_handler: ConstraintHandler):
        """
        Initialize feasible population generator.
        
        Args:
            constraint_handler: ConstraintHandler instance for constraint validation
        """
        self.constraint_handler = constraint_handler
        self.logger = logging.getLogger(__name__)
        self.generation_attempts = 0
        self.repair_attempts = 0
        self.successful_generations = 0
        self.successful_repairs = 0
    
    def generate_feasible_individual(self, instance: Dict[str, Any]) -> List[int]:
        """
        Generate a single feasible individual that respects the vehicle constraint.
        
        This method creates constraint-satisfying solutions by generating random
        permutations and validating them against the vehicle limit, regenerating
        until a feasible solution is found.
        
        Args:
            instance: Problem instance data
            
        Returns:
            List representing a feasible route sequence
            
        Raises:
            RuntimeError: If unable to generate feasible solution after maximum attempts
        """
        num_customers = instance['Number_of_customers']
        max_attempts = self.constraint_handler.config.repair_attempts * 10  # More attempts for generation
        
        for attempt in range(max_attempts):
            self.generation_attempts += 1
            
            # Generate random permutation of customers
            individual = random.sample(range(1, num_customers + 1), num_customers)
            
            # Check if solution is feasible
            if self.constraint_handler.validate_solution(individual, instance):
                self.successful_generations += 1
                self.logger.debug(f"Generated feasible individual after {attempt + 1} attempts")
                return individual
            
            # If not feasible, try repair mechanism
            repaired_individual = self.repair_infeasible_solution(individual, instance)
            if repaired_individual is not None:
                self.successful_generations += 1
                self.logger.debug(f"Generated feasible individual via repair after {attempt + 1} attempts")
                return repaired_individual
        
        # If we reach here, we couldn't generate a feasible solution
        error_msg = (f"Failed to generate feasible individual after {max_attempts} attempts. "
                    f"Vehicle constraint ({self.constraint_handler.config.max_vehicles}) may be too restrictive.")
        self.logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    def generate_feasible_population(self, instance: Dict[str, Any], population_size: int) -> List[List[int]]:
        """
        Generate an entire population of feasible individuals.
        
        Creates a population where all individuals satisfy the vehicle constraint,
        ensuring diversity while maintaining feasibility.
        
        Args:
            instance: Problem instance data
            population_size: Number of individuals to generate
            
        Returns:
            List of feasible individuals
            
        Raises:
            RuntimeError: If unable to generate required number of feasible individuals
        """
        population = []
        failed_generations = 0
        max_failed_attempts = population_size // 2  # Allow some failures
        
        self.logger.info(f"Generating feasible population of size {population_size}")
        
        for i in range(population_size):
            try:
                individual = self.generate_feasible_individual(instance)
                population.append(individual)
                
                if (i + 1) % 10 == 0:  # Log progress every 10 individuals
                    self.logger.debug(f"Generated {i + 1}/{population_size} feasible individuals")
                    
            except RuntimeError as e:
                failed_generations += 1
                self.logger.warning(f"Failed to generate individual {i + 1}: {e}")
                
                if failed_generations > max_failed_attempts:
                    error_msg = (f"Failed to generate feasible population. "
                                f"Generated {len(population)}/{population_size} individuals. "
                                f"Vehicle constraint may be too restrictive.")
                    self.logger.error(error_msg)
                    raise RuntimeError(error_msg)
        
        # Verify all individuals are feasible
        feasible_count = sum(1 for ind in population 
                           if self.constraint_handler.validate_solution(ind, instance))
        
        if feasible_count != len(population):
            self.logger.warning(f"Population verification failed: {feasible_count}/{len(population)} feasible")
        
        self.logger.info(f"Successfully generated {len(population)} feasible individuals")
        return population
    
    def repair_infeasible_solution(self, individual: List[int], instance: Dict[str, Any]) -> Optional[List[int]]:
        """
        Repair an infeasible solution to make it satisfy constraints.
        
        Implements solution repair mechanisms that attempt to reduce the number
        of vehicles by reordering customers to better utilize vehicle capacity.
        
        Args:
            individual: Infeasible route sequence
            instance: Problem instance data
            
        Returns:
            Repaired feasible solution or None if repair failed
        """
        if self.constraint_handler.validate_solution(individual, instance):
            return individual  # Already feasible
        
        self.repair_attempts += 1
        
        # Try multiple repair strategies
        repair_strategies = [
            self._repair_by_capacity_optimization,
            self._repair_by_route_merging,
            self._repair_by_customer_reordering
        ]
        
        for strategy in repair_strategies:
            try:
                repaired = strategy(individual.copy(), instance)
                if repaired is not None and self.constraint_handler.validate_solution(repaired, instance):
                    self.successful_repairs += 1
                    self.logger.debug(f"Successfully repaired solution using {strategy.__name__}")
                    return repaired
            except Exception as e:
                self.logger.debug(f"Repair strategy {strategy.__name__} failed: {e}")
                continue
        
        self.logger.debug("All repair strategies failed")
        return None
    
    def _repair_by_capacity_optimization(self, individual: List[int], instance: Dict[str, Any]) -> Optional[List[int]]:
        """
        Repair solution by optimizing vehicle capacity utilization.
        
        Reorders customers to maximize vehicle capacity usage, potentially
        reducing the number of vehicles needed.
        """
        # Sort customers by demand in descending order to pack efficiently
        customers_with_demand = [(customer_id, instance[f'customer_{customer_id}']['demand']) 
                               for customer_id in individual]
        customers_with_demand.sort(key=lambda x: x[1], reverse=True)
        
        # Create new ordering based on capacity optimization
        repaired = [customer_id for customer_id, _ in customers_with_demand]
        
        return repaired if self.constraint_handler.validate_solution(repaired, instance) else None
    
    def _repair_by_route_merging(self, individual: List[int], instance: Dict[str, Any]) -> Optional[List[int]]:
        """
        Repair solution by attempting to merge routes to reduce vehicle count.
        
        Analyzes current routes and tries to combine them while respecting
        vehicle capacity constraints.
        """
        # Get current route structure
        routes = routeToSubroute(individual, instance)
        vehicle_capacity = instance['vehicle_capacity']
        
        # Try to merge routes with low utilization
        merged_routes = []
        i = 0
        
        while i < len(routes):
            current_route = routes[i]
            current_load = sum(instance[f'customer_{customer_id}']['demand'] 
                             for customer_id in current_route)
            
            # Try to merge with next route if possible
            if i + 1 < len(routes):
                next_route = routes[i + 1]
                next_load = sum(instance[f'customer_{customer_id}']['demand'] 
                              for customer_id in next_route)
                
                if current_load + next_load <= vehicle_capacity:
                    # Merge routes
                    merged_route = current_route + next_route
                    merged_routes.append(merged_route)
                    i += 2  # Skip next route as it's been merged
                    continue
            
            merged_routes.append(current_route)
            i += 1
        
        # Convert back to individual representation
        repaired = []
        for route in merged_routes:
            repaired.extend(route)
        
        return repaired if len(repaired) == len(individual) else None
    
    def _repair_by_customer_reordering(self, individual: List[int], instance: Dict[str, Any]) -> Optional[List[int]]:
        """
        Repair solution by reordering customers to improve vehicle utilization.
        
        Uses a greedy approach to reorder customers based on demand and
        spatial proximity to reduce vehicle requirements.
        """
        num_customers = len(individual)
        vehicle_capacity = instance['vehicle_capacity']
        
        # Greedy construction: build routes one by one
        remaining_customers = set(individual)
        repaired = []
        
        while remaining_customers:
            # Start new route with customer having highest demand that fits
            route_customers = []
            current_capacity = 0
            
            # Find customers that can fit in current route
            available_customers = list(remaining_customers)
            
            # Sort by demand (descending) to fill routes efficiently
            available_customers.sort(
                key=lambda x: instance[f'customer_{x}']['demand'], 
                reverse=True
            )
            
            for customer_id in available_customers:
                demand = instance[f'customer_{customer_id}']['demand']
                if current_capacity + demand <= vehicle_capacity:
                    route_customers.append(customer_id)
                    current_capacity += demand
                    remaining_customers.remove(customer_id)
            
            if not route_customers:
                # No customers can fit, this shouldn't happen with valid data
                break
            
            repaired.extend(route_customers)
        
        return repaired if len(repaired) == num_customers else None
    
    def regenerate_until_feasible(self, instance: Dict[str, Any], max_attempts: Optional[int] = None) -> List[int]:
        """
        Regenerate solutions until a feasible one is found.
        
        Implements regeneration logic for infeasible solutions with configurable
        maximum attempts and fallback strategies.
        
        Args:
            instance: Problem instance data
            max_attempts: Maximum regeneration attempts (uses config if None)
            
        Returns:
            Feasible individual
            
        Raises:
            RuntimeError: If unable to generate feasible solution
        """
        if max_attempts is None:
            max_attempts = self.constraint_handler.config.repair_attempts * 5
        
        for attempt in range(max_attempts):
            try:
                individual = self.generate_feasible_individual(instance)
                self.logger.debug(f"Regenerated feasible solution after {attempt + 1} attempts")
                return individual
            except RuntimeError:
                if attempt == max_attempts - 1:
                    # Last attempt failed
                    error_msg = (f"Failed to regenerate feasible solution after {max_attempts} attempts. "
                                f"Consider relaxing vehicle constraint or checking problem feasibility.")
                    self.logger.error(error_msg)
                    raise RuntimeError(error_msg)
                continue
        
        # This should never be reached due to the exception handling above
        raise RuntimeError("Unexpected error in regeneration logic")
    
    def validate_population_feasibility(self, population: List[List[int]], instance: Dict[str, Any]) -> Tuple[int, int, float]:
        """
        Validate feasibility of an entire population.
        
        Args:
            population: List of individuals to validate
            instance: Problem instance data
            
        Returns:
            Tuple of (feasible_count, total_count, feasibility_ratio)
        """
        if not population:
            return 0, 0, 0.0
        
        feasible_count = 0
        total_count = len(population)
        
        for individual in population:
            if self.constraint_handler.validate_solution(individual, instance):
                feasible_count += 1
        
        feasibility_ratio = feasible_count / total_count if total_count > 0 else 0.0
        
        self.logger.info(f"Population feasibility: {feasible_count}/{total_count} ({feasibility_ratio:.2%})")
        
        return feasible_count, total_count, feasibility_ratio
    
    def detect_infeasibility_conflict(self, instance: Dict[str, Any]) -> Optional[str]:
        """
        Detect if the constraint configuration makes the problem infeasible.
        
        Analyzes the problem instance to determine if the vehicle constraint
        is too restrictive given the customer demands and vehicle capacity.
        
        Args:
            instance: Problem instance data
            
        Returns:
            Error message if infeasibility detected, None otherwise
        """
        try:
            # Calculate minimum vehicles needed based on total demand
            total_demand = sum(instance[f'customer_{i}']['demand'] 
                             for i in range(1, instance['Number_of_customers'] + 1))
            vehicle_capacity = instance['vehicle_capacity']
            min_vehicles_needed = int(total_demand / vehicle_capacity) + (1 if total_demand % vehicle_capacity > 0 else 0)
            
            max_vehicles_allowed = self.constraint_handler.config.max_vehicles
            
            if min_vehicles_needed > max_vehicles_allowed:
                return (f"Infeasibility detected: Minimum vehicles needed ({min_vehicles_needed}) "
                       f"exceeds maximum allowed ({max_vehicles_allowed}). "
                       f"Total demand: {total_demand}, Vehicle capacity: {vehicle_capacity}")
            
            # Check for individual customers with demand exceeding capacity
            oversized_customers = []
            for i in range(1, instance['Number_of_customers'] + 1):
                demand = instance[f'customer_{i}']['demand']
                if demand > vehicle_capacity:
                    oversized_customers.append((i, demand))
            
            if oversized_customers:
                return (f"Infeasibility detected: Customers with demand exceeding vehicle capacity: "
                       f"{oversized_customers}. Vehicle capacity: {vehicle_capacity}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting infeasibility: {e}")
            return f"Error analyzing problem feasibility: {e}"
    
    def get_generation_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about population generation and repair operations.
        
        Returns:
            Dictionary containing generation and repair statistics
        """
        generation_success_rate = (self.successful_generations / self.generation_attempts 
                                 if self.generation_attempts > 0 else 0.0)
        repair_success_rate = (self.successful_repairs / self.repair_attempts 
                             if self.repair_attempts > 0 else 0.0)
        
        return {
            'generation_attempts': self.generation_attempts,
            'successful_generations': self.successful_generations,
            'generation_success_rate': generation_success_rate,
            'repair_attempts': self.repair_attempts,
            'successful_repairs': self.successful_repairs,
            'repair_success_rate': repair_success_rate
        }
    
    def reset_statistics(self):
        """Reset generation and repair statistics."""
        self.generation_attempts = 0
        self.repair_attempts = 0
        self.successful_generations = 0
        self.successful_repairs = 0


def create_feasible_generator(instance: Dict[str, Any], 
                            max_vehicles: Optional[int] = None,
                            penalty_method: str = "static_penalty",
                            penalty_factor: float = 1000.0,
                            repair_attempts: int = 3,
                            feasibility_threshold: float = 0.8) -> FeasiblePopulationGenerator:
    """
    Factory function to create a FeasiblePopulationGenerator with proper configuration.
    
    Args:
        instance: Problem instance data
        max_vehicles: Maximum vehicles constraint (uses instance data if None)
        penalty_method: Penalty method for constraint violations
        penalty_factor: Base penalty factor
        repair_attempts: Number of repair attempts for infeasible solutions
        feasibility_threshold: Minimum feasibility ratio to maintain
        
    Returns:
        Configured FeasiblePopulationGenerator instance
    """
    # Determine max vehicles from instance or parameter
    if max_vehicles is None:
        max_vehicles = instance.get('max_vehicle_number', 20)
    
    # Create constraint configuration
    config = ConstraintConfig(
        max_vehicles=max_vehicles,
        penalty_method=penalty_method,
        penalty_factor=penalty_factor,
        repair_attempts=repair_attempts,
        feasibility_threshold=feasibility_threshold
    )
    
    # Create constraint handler
    constraint_handler = ConstraintHandler(config)
    
    # Create and return feasible generator
    return FeasiblePopulationGenerator(constraint_handler)


def generate_initial_feasible_population(instance: Dict[str, Any], 
                                       population_size: int,
                                       max_vehicles: Optional[int] = None) -> List[List[int]]:
    """
    Convenience function to generate an initial feasible population.
    
    Args:
        instance: Problem instance data
        population_size: Number of individuals to generate
        max_vehicles: Maximum vehicles constraint (uses instance data if None)
        
    Returns:
        List of feasible individuals
        
    Raises:
        RuntimeError: If unable to generate feasible population
    """
    generator = create_feasible_generator(instance, max_vehicles)
    
    # Check for infeasibility conflicts before generation
    conflict = generator.detect_infeasibility_conflict(instance)
    if conflict:
        raise RuntimeError(f"Problem infeasibility detected: {conflict}")
    
    return generator.generate_feasible_population(instance, population_size)