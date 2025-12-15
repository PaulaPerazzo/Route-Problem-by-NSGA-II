from nsga.NSGA2 import *
from nsga.constraint_handler import ConstraintConfig, ConstraintHandler, validate_constraint_parameters, ConstraintError
from nsga.enhanced_fitness_evaluator import EnhancedFitnessEvaluator
import argparse
import sys
import logging

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="NSGA-II Vehicle Routing Optimization with Constraint Handling")
    
    # Original parameters
    parser.add_argument('--instance_name', type=str, default="./data/json/Input_Data.json", required=False,
                        help="Enter the input Json file name")
    parser.add_argument('--popSize', type=int, default=400, required=False,
                        help="Enter the population size")
    parser.add_argument('--crossProb', type=float, default=0.85, required=False,
                        help="Crossover Probability")
    parser.add_argument('--mutProb', type=float, default=0.02, required=False,
                        help="Mutation Probabilty")
    parser.add_argument('--numGen', type=int, default=200, required=False,
                        help="Number of generations to run")
    
    # New constraint parameters
    parser.add_argument('--max_vehicles', type=int, default=20, required=False,
                        help="Maximum number of vehicles allowed (default: 20)")
    parser.add_argument('--penalty_method', type=str, default="static_penalty", 
                        choices=["death_penalty", "static_penalty", "dynamic_penalty"], required=False,
                        help="Penalty method for constraint violations (default: static_penalty)")
    parser.add_argument('--penalty_factor', type=float, default=1000.0, required=False,
                        help="Base penalty factor for constraint violations (default: 1000.0)")
    parser.add_argument('--repair_attempts', type=int, default=3, required=False,
                        help="Number of attempts to repair infeasible solutions (default: 3)")
    parser.add_argument('--feasibility_threshold', type=float, default=0.8, required=False,
                        help="Minimum proportion of feasible solutions to maintain (default: 0.8)")
    parser.add_argument('--enable_constraint_logging', action='store_true', 
                        help="Enable detailed constraint violation logging")

    args = parser.parse_args()

    try:
        # Validate command-line constraint parameters
        validate_command_line_constraints(args)
        
        # Validate constraint parameters using the constraint handler
        validate_constraint_parameters(args.max_vehicles, args.penalty_method, args.penalty_factor)
        
        # Load instance
        json_instance = load_instance(args.instance_name)
        if json_instance is None:
            logger.error(f"Failed to load instance file: {args.instance_name}")
            sys.exit(1)
        
        # Create constraint configuration
        constraint_config = ConstraintConfig(
            max_vehicles=args.max_vehicles,
            penalty_method=args.penalty_method,
            penalty_factor=args.penalty_factor,
            repair_attempts=args.repair_attempts,
            feasibility_threshold=args.feasibility_threshold
        )
        
        # Create constraint handler
        constraint_handler = ConstraintHandler(constraint_config)
        
        # Create enhanced fitness evaluator
        enhanced_evaluator = EnhancedFitnessEvaluator(constraint_handler)
        
        # Set up detailed logging if requested
        if args.enable_constraint_logging:
            logging.getLogger('nsga.constraint_handler').setLevel(logging.DEBUG)
            logging.getLogger('nsga.enhanced_fitness_evaluator').setLevel(logging.DEBUG)
        
        # Display configuration
        logger.info("=== NSGA-II Constrained Vehicle Routing Optimization ===")
        logger.info(f"Instance: {args.instance_name}")
        logger.info(f"Population Size: {args.popSize}")
        logger.info(f"Crossover Probability: {args.crossProb}")
        logger.info(f"Mutation Probability: {args.mutProb}")
        logger.info(f"Number of Generations: {args.numGen}")
        logger.info(f"Maximum Vehicles: {args.max_vehicles}")
        logger.info(f"Penalty Method: {args.penalty_method}")
        logger.info(f"Penalty Factor: {args.penalty_factor}")
        logger.info(f"Repair Attempts: {args.repair_attempts}")
        logger.info(f"Feasibility Threshold: {args.feasibility_threshold}")
        
        # Create NSGA-II algorithm instance
        nsgaObj = nsgaAlgo()
        
        # Set parameters
        nsgaObj.json_instance = json_instance
        nsgaObj.pop_size = args.popSize
        nsgaObj.cross_prob = args.crossProb
        nsgaObj.mut_prob = args.mutProb
        nsgaObj.num_gen = args.numGen
        
        # Add constraint handling components
        nsgaObj.constraint_handler = constraint_handler
        nsgaObj.enhanced_evaluator = enhanced_evaluator
        nsgaObj.constraint_config = constraint_config
        
        # Run optimization
        logger.info("Starting constrained optimization...")
        nsgaObj.runMain()
        
        # Display constraint satisfaction results
        display_constraint_results(nsgaObj, enhanced_evaluator, constraint_handler, logger)
        
    except ConstraintError as e:
        logger.error(f"Constraint configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        sys.exit(1)


def display_constraint_results(nsga_obj, enhanced_evaluator, constraint_handler, logger):
    """
    Display comprehensive constraint satisfaction results.
    
    Args:
        nsga_obj: NSGA-II algorithm instance
        enhanced_evaluator: EnhancedFitnessEvaluator instance
        constraint_handler: ConstraintHandler instance
        logger: Logger instance
    """
    logger.info("=== CONSTRAINT SATISFACTION RESULTS ===")
    
    # Get evaluation statistics
    eval_stats = enhanced_evaluator.get_evaluation_statistics()
    constraint_stats = constraint_handler.get_statistics()
    
    # Display evaluation statistics
    logger.info(f"Total Evaluations: {eval_stats['total_evaluations']}")
    logger.info(f"Feasible Solutions: {eval_stats['feasible_evaluations']}")
    logger.info(f"Infeasible Solutions: {eval_stats['infeasible_evaluations']}")
    logger.info(f"Feasibility Ratio: {eval_stats['feasibility_ratio']:.2%}")
    
    # Display constraint violation statistics
    logger.info(f"Constraint Violations Detected: {constraint_stats['violation_count']}")
    logger.info(f"Penalty Applications: {constraint_stats['penalty_applications']}")
    
    # Validate final population constraint satisfaction
    if hasattr(nsga_obj, 'pop') and nsga_obj.pop:
        feasible_final = 0
        infeasible_final = 0
        max_vehicles_in_final = 0
        
        for individual in nsga_obj.pop:
            num_vehicles = getNumVehiclesRequired(individual, nsga_obj.json_instance)
            max_vehicles_in_final = max(max_vehicles_in_final, num_vehicles)
            
            if constraint_handler.validate_solution(individual, nsga_obj.json_instance):
                feasible_final += 1
            else:
                infeasible_final += 1
        
        final_feasibility_ratio = feasible_final / len(nsga_obj.pop) if nsga_obj.pop else 0.0
        
        logger.info("=== FINAL POPULATION ANALYSIS ===")
        logger.info(f"Final Population Size: {len(nsga_obj.pop)}")
        logger.info(f"Feasible Solutions in Final Population: {feasible_final}")
        logger.info(f"Infeasible Solutions in Final Population: {infeasible_final}")
        logger.info(f"Final Feasibility Ratio: {final_feasibility_ratio:.2%}")
        logger.info(f"Maximum Vehicles in Final Population: {max_vehicles_in_final}")
        logger.info(f"Vehicle Constraint Limit: {constraint_handler.config.max_vehicles}")
        
        # Check constraint satisfaction status
        if infeasible_final == 0:
            logger.info("✓ SUCCESS: All final solutions satisfy the vehicle constraint!")
        else:
            logger.warning(f"⚠ WARNING: {infeasible_final} solutions in final population violate constraints")
        
        # Display best solution constraint status
        if hasattr(nsga_obj, 'best_individual') and nsga_obj.best_individual:
            best_vehicles = getNumVehiclesRequired(nsga_obj.best_individual, nsga_obj.json_instance)
            best_is_feasible = constraint_handler.validate_solution(nsga_obj.best_individual, nsga_obj.json_instance)
            
            logger.info("=== BEST SOLUTION CONSTRAINT STATUS ===")
            logger.info(f"Best Solution Vehicles: {best_vehicles}")
            logger.info(f"Best Solution Cost: {nsga_obj.best_individual.fitness.values[1]:.2f}")
            logger.info(f"Best Solution Feasible: {'✓ YES' if best_is_feasible else '✗ NO'}")
            
            if not best_is_feasible:
                violation = best_vehicles - constraint_handler.config.max_vehicles
                logger.warning(f"Best solution violates constraint by {violation} vehicles")
    
    # Display configuration summary
    logger.info("=== CONSTRAINT CONFIGURATION SUMMARY ===")
    config_dict = constraint_handler.config.to_dict()
    for key, value in config_dict.items():
        logger.info(f"{key.replace('_', ' ').title()}: {value}")


def validate_command_line_constraints(args):
    """
    Validate command-line constraint parameters.
    
    Args:
        args: Parsed command-line arguments
        
    Raises:
        ConstraintError: If parameters are invalid
    """
    try:
        # Validate max_vehicles
        if args.max_vehicles <= 0:
            raise ConstraintError(f"max_vehicles must be positive, got {args.max_vehicles}")
        
        # Validate penalty_factor
        if args.penalty_factor < 0:
            raise ConstraintError(f"penalty_factor must be non-negative, got {args.penalty_factor}")
        
        # Validate repair_attempts
        if args.repair_attempts < 0:
            raise ConstraintError(f"repair_attempts must be non-negative, got {args.repair_attempts}")
        
        # Validate feasibility_threshold
        if not (0.0 <= args.feasibility_threshold <= 1.0):
            raise ConstraintError(f"feasibility_threshold must be between 0.0 and 1.0, got {args.feasibility_threshold}")
        
        # Validate penalty_method (already handled by choices in argparse, but double-check)
        valid_methods = ["death_penalty", "static_penalty", "dynamic_penalty"]
        if args.penalty_method not in valid_methods:
            raise ConstraintError(f"penalty_method must be one of {valid_methods}, got {args.penalty_method}")
            
    except Exception as e:
        raise ConstraintError(f"Command-line parameter validation failed: {e}")


if __name__ == '__main__':
    main()
