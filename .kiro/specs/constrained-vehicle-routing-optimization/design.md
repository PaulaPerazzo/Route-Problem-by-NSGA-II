# Design Document: Constrained Vehicle Routing Optimization

## Overview

This design addresses the constraint violation issue in the current NSGA-II vehicle routing optimization system. The current implementation treats vehicle count as a minimization objective without enforcing the hard constraint of maximum 20 vehicles. This design introduces proper constraint handling mechanisms while maintaining the multi-objective optimization of vehicle count and transportation cost.

The solution implements a constraint-handling approach that combines penalty methods with feasibility preservation techniques, ensuring all final solutions respect the vehicle limit while optimizing both objectives effectively.

## Architecture

The system follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────┐
│           Optimization Layer            │
│  ┌─────────────────┐ ┌─────────────────┐│
│  │   NSGA-II Core  │ │ Constraint      ││
│  │   Algorithm     │ │ Handler         ││
│  └─────────────────┘ └─────────────────┘│
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│          Evaluation Layer               │
│  ┌─────────────────┐ ┌─────────────────┐│
│  │ Multi-Objective │ │ Feasibility     ││
│  │ Fitness         │ │ Checker         ││
│  └─────────────────┘ └─────────────────┘│
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│           Problem Layer                 │
│  ┌─────────────────┐ ┌─────────────────┐│
│  │ Route Generator │ │ VRP Instance    ││
│  │ & Decoder       │ │ Data            ││
│  └─────────────────┘ └─────────────────┘│
└─────────────────────────────────────────┘
```

## Components and Interfaces

### ConstraintHandler
- **Purpose**: Manages constraint validation and penalty application
- **Key Methods**:
  - `validate_solution(individual, max_vehicles)`: Returns feasibility status
  - `apply_penalty(fitness_values, violation_degree)`: Modifies fitness for infeasible solutions
  - `get_violation_degree(individual, max_vehicles)`: Quantifies constraint violation

### EnhancedFitnessEvaluator
- **Purpose**: Evaluates solutions considering both objectives and constraints
- **Key Methods**:
  - `evaluate_constrained_fitness(individual, instance, max_vehicles, unit_cost)`: Returns constrained fitness
  - `calculate_penalty_factor(violation_degree)`: Computes penalty magnitude

### FeasiblePopulationGenerator
- **Purpose**: Generates initial populations that respect constraints
- **Key Methods**:
  - `generate_feasible_individual(instance, max_vehicles)`: Creates constraint-satisfying solution
  - `repair_infeasible_solution(individual, instance, max_vehicles)`: Fixes constraint violations

### ConstraintPreservingOperators
- **Purpose**: Genetic operators that maintain feasibility
- **Key Methods**:
  - `constrained_crossover(parent1, parent2, instance, max_vehicles)`: Feasibility-preserving crossover
  - `constrained_mutation(individual, instance, max_vehicles)`: Feasibility-preserving mutation

## Data Models

### ConstrainedSolution
```python
class ConstrainedSolution:
    route_sequence: List[int]
    vehicle_count: int
    total_cost: float
    is_feasible: bool
    constraint_violation: float
    penalty_applied: bool
```

### ConstraintConfig
```python
class ConstraintConfig:
    max_vehicles: int
    penalty_method: str  # "death_penalty", "static_penalty", "dynamic_penalty"
    penalty_factor: float
    repair_attempts: int
    feasibility_threshold: float
```

### OptimizationResult
```python
class OptimizationResult:
    pareto_front: List[ConstrainedSolution]
    feasible_solutions_count: int
    constraint_violations_detected: int
    convergence_metrics: Dict[str, float]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Property 1: Constraint verification universality
*For any* solution evaluation, the system should always check that the vehicle count does not exceed the maximum vehicle constraint
**Validates: Requirements 1.1**

Property 2: Infeasible solution classification
*For any* solution that exceeds the vehicle constraint, the system should classify it as infeasible
**Validates: Requirements 1.2**

Property 3: Penalty application consistency
*For any* infeasible solution, the system should apply constraint penalties that make it less favorable than equivalent feasible solutions
**Validates: Requirements 1.3**

Property 4: Final population feasibility
*For any* completed optimization run, all solutions in the final population should satisfy the vehicle constraint
**Validates: Requirements 1.4**

Property 5: Result display constraint validation
*For any* displayed optimization result, the shown vehicle counts should be within the constraint limit
**Validates: Requirements 1.5**

Property 6: Dual objective calculation
*For any* feasible solution evaluation, the system should calculate both vehicle count and transportation cost
**Validates: Requirements 2.1**

Property 7: Pareto dominance correctness
*For any* pair of solutions, the dominance relationship should consider both vehicle count and cost objectives simultaneously
**Validates: Requirements 2.2**

Property 8: Pareto front non-dominance
*For any* final Pareto front, no solution should dominate any other solution in the set
**Validates: Requirements 2.5**

Property 9: Configuration constraint loading
*For any* system initialization, the vehicle constraint should be correctly read from the configuration file
**Validates: Requirements 3.1**

Property 10: Dynamic constraint application
*For any* constraint modification during runtime, all subsequent evaluations should use the new constraint value
**Validates: Requirements 3.2**

Property 11: Penalty strategy configuration
*For any* configured penalty method, the system should apply that specific strategy to infeasible solutions
**Validates: Requirements 3.3**

Property 12: Constraint violation logging
*For any* optimization run, constraint violations and penalty applications should be logged for monitoring
**Validates: Requirements 3.4**

Property 13: Invalid configuration rejection
*For any* invalid constraint parameters, the system should reject the configuration with clear error messages
**Validates: Requirements 3.5**

Property 14: Initial population feasibility
*For any* generated initial population, all individuals should satisfy the vehicle constraint
**Validates: Requirements 4.1, 4.3**

Property 15: Regeneration until feasible
*For any* constraint-violating generated solution, the system should regenerate until a feasible solution is created
**Validates: Requirements 4.2**

Property 16: Crossover feasibility preservation
*For any* crossover operation on feasible parents, the resulting offspring should respect the vehicle constraint
**Validates: Requirements 5.1**

Property 17: Mutation constraint verification
*For any* mutation operation, the system should verify constraint satisfaction after modification
**Validates: Requirements 5.2**

Property 18: Repair mechanism activation
*For any* infeasible offspring produced by genetic operators, repair mechanisms should be applied to restore feasibility
**Validates: Requirements 5.3**

Property 19: Population feasibility ratio maintenance
*For any* generation after genetic operations, the proportion of feasible solutions should remain above a specified threshold
**Validates: Requirements 5.5**

Property 20: Comprehensive constraint detection
*For any* diverse set of solutions, the system should correctly identify all constraint violations
**Validates: Requirements 6.1**

Property 21: Penalty effectiveness
*For any* penalized solution, it should have worse fitness than equivalent feasible solutions during selection
**Validates: Requirements 6.2**

Property 22: Final result validation
*For any* returned optimization result, all solutions should be both non-dominated and feasible
**Validates: Requirements 6.3**

Property 23: Cross-instance consistency
*For any* different problem instance, constraint handling should maintain consistent behavior
**Validates: Requirements 6.5**

## Error Handling

The system implements comprehensive error handling for constraint-related issues:

### Constraint Violation Handling
- **Detection**: Immediate identification of solutions exceeding vehicle limits
- **Response**: Application of configurable penalty mechanisms
- **Recovery**: Repair mechanisms to restore feasibility when possible

### Configuration Error Handling
- **Validation**: Input parameter validation during system initialization
- **Feedback**: Clear error messages for invalid configurations
- **Fallback**: Default constraint values when configuration is missing

### Optimization Failure Handling
- **Infeasibility Detection**: Recognition when constraints make problems unsolvable
- **User Notification**: Clear reporting of constraint conflicts
- **Guidance**: Suggestions for parameter adjustments to achieve feasibility

## Testing Strategy

The testing approach combines unit testing and property-based testing to ensure comprehensive validation:

### Unit Testing Approach
- **Constraint Validation**: Test specific constraint checking functions with known inputs
- **Penalty Mechanisms**: Verify different penalty strategies produce expected fitness modifications
- **Configuration Loading**: Test configuration parsing and validation with various input formats
- **Edge Cases**: Test boundary conditions like exactly 20 vehicles, empty solutions, single-vehicle solutions

### Property-Based Testing Approach
- **Testing Framework**: Use Hypothesis (Python) for property-based testing with minimum 100 iterations per property
- **Generator Strategy**: Create smart generators that produce both feasible and infeasible solutions across the constraint space
- **Constraint Properties**: Each correctness property will be implemented as a separate property-based test
- **Test Tagging**: Each property-based test will be tagged with the format: '**Feature: constrained-vehicle-routing-optimization, Property {number}: {property_text}**'

### Integration Testing
- **End-to-End Validation**: Test complete optimization runs with various problem instances
- **Constraint Consistency**: Verify constraint handling across different genetic operators
- **Performance Impact**: Measure the computational overhead of constraint handling mechanisms

### Test Data Strategy
- **Synthetic Instances**: Generate problem instances with known constraint characteristics
- **Boundary Testing**: Create instances that test constraint limits and edge cases
- **Regression Testing**: Maintain test suite for different problem sizes and constraint configurations