"""
Demonstration script for VRPTW (Vehicle Routing Problem with Time Windows)

This script shows how the time window constraints are being enforced in the NSGA-II algorithm.
"""

from nsga.NSGA2 import load_instance, getTimeWindowViolation, routeToSubroute
import random

def demonstrate_time_windows():
    print("="*60)
    print("VRPTW - Time Window Constraints Demonstration")
    print("="*60)
    
    # Load instance
    instance = load_instance('./data/json/Input_Data.json')
    
    print(f"\nInstance Information:")
    print(f"  - Number of customers: {instance['Number_of_customers']}")
    print(f"  - Vehicle capacity: {instance['vehicle_capacity']}")
    print(f"  - Depot time window: [{instance['depart']['ready_time']}, {instance['depart']['due_time']}]")
    
    # Show some customer time windows
    print(f"\nSample Customer Time Windows:")
    for i in [1, 10, 50, 100]:
        customer = instance[f'customer_{i}']
        print(f"  Customer {i:3d}: [{customer['ready_time']:6.1f}, {customer['due_time']:6.1f}] "
              f"(service time: {customer['service_time']:4.1f}, demand: {customer['demand']:5.1f})")
    
    # Generate a random solution
    individual = list(range(1, instance['Number_of_customers'] + 1))
    random.shuffle(individual)
    
    print(f"\nAnalyzing a random solution...")
    
    # Calculate metrics
    routes = routeToSubroute(individual, instance)
    violations = getTimeWindowViolation(individual, instance)
    
    print(f"  - Number of routes: {len(routes)}")
    print(f"  - Total time window violations: {violations:.2f}")
    
    if violations > 0:
        print(f"\n⚠️  This solution violates time windows!")
        print(f"   Total delay beyond due times: {violations:.2f} time units")
    else:
        print(f"\n✅ This solution respects all time windows!")
    
    # Show first route details
    if routes:
        print(f"\nFirst Route Details:")
        print(f"  Route: 0 (depot) -> {' -> '.join(map(str, routes[0]))} -> 0 (depot)")
        
        # Calculate arrival times for first route
        current_time = 0
        last_customer = 0
        print(f"\n  Time Schedule:")
        print(f"    Start at depot: time 0.00")
        
        for customer_id in routes[0][:3]:  # Show first 3 customers
            travel_time = instance["distance_matrix"][last_customer][customer_id]
            arrival_time = current_time + travel_time
            
            customer = instance[f"customer_{customer_id}"]
            ready_time = customer["ready_time"]
            due_time = customer["due_time"]
            service_time = customer["service_time"]
            
            status = "✅ On time"
            if arrival_time < ready_time:
                status = f"⏰ Early (wait {ready_time - arrival_time:.1f})"
                current_time = ready_time + service_time
            elif arrival_time > due_time:
                status = f"❌ Late (delay {arrival_time - due_time:.1f})"
                current_time = arrival_time + service_time
            else:
                current_time = arrival_time + service_time
            
            print(f"    Customer {customer_id:2d}: arrive {arrival_time:6.2f}, "
                  f"window [{ready_time:6.1f}, {due_time:6.1f}] - {status}")
            
            last_customer = customer_id
    
    print("\n" + "="*60)
    print("The NSGA-II algorithm minimizes these violations while also")
    print("optimizing vehicle count and total distance traveled.")
    print("="*60 + "\n")

if __name__ == "__main__":
    demonstrate_time_windows()
