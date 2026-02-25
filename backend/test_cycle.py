#!/usr/bin/env python
# Test cycle detection logic
remaining_debts = {
    (1, 2): 10,  # Bob -> Alice
    (2, 3): 10,  # Alice -> Cara
    (3, 1): 10,  # Cara -> Bob
}

def find_and_remove_one_cycle():
    """Find one cycle in remaining debts and reduce it. Return True if a cycle was found."""
    # Build adjacency for DFS
    adj = {}
    for debtor, creditor in remaining_debts:
        if debtor not in adj:
            adj[debtor] = []
        adj[debtor].append(creditor)
    
    print(f"Adjacency: {adj}")
    
    # Try to find a cycle using DFS from each node
    def find_cycle_from(start):
        """Use DFS to find a cycle starting from 'start'."""
        stack = [(start, [start])]  # (current_node, path)
        
        while stack:
            node, path = stack.pop()
            
            if node in adj:
                for neighbor in adj[node]:
                    if neighbor == start and len(path) > 1:
                        # Found a cycle!
                        return path + [start]
                    elif neighbor not in path:
                        stack.append((neighbor, path + [neighbor]))
        
        return None
    
    # Try to find a cycle from each node
    for start_node in adj:
        cycle = find_cycle_from(start_node)
        if cycle:
            print(f"Found cycle: {cycle}")
            # Found a cycle [A, B, C, A, ...]
            # Remove the duplicate last element
            cycle = cycle[:-1]
            print(f"Cycle without duplicate: {cycle}")
            
            # Calculate minimum amount in this cycle
            min_amount = float('inf')
            for i in range(len(cycle)):
                u1 = cycle[i]
                u2 = cycle[(i + 1) % len(cycle)]
                if (u1, u2) in remaining_debts:
                    min_amount = min(min_amount, remaining_debts[(u1, u2)])
            
            print(f"Min amount: {min_amount}")
            
            if min_amount > 0:
                # Reduce all edges in the cycle by min_amount
                for i in range(len(cycle)):
                    u1 = cycle[i]
                    u2 = cycle[(i + 1) % len(cycle)]
                    key = (u1, u2)
                    
                    remaining_debts[key] -= min_amount
                    if remaining_debts[key] <= 0.001:
                        del remaining_debts[key]
                
                return True
    
    return False

# Test it
count = 0
while find_and_remove_one_cycle() and count < 5:
    print(f"Remaining debts: {remaining_debts}")
    count += 1

print(f"Final remaining debts: {remaining_debts}")
