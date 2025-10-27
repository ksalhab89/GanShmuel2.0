"""Test suite to verify the corrected weight calculation logic."""

import pytest
from src.utils.calculations import calculate_net_weight, calculate_truck_tara


class TestCorrectedWeightCalculations:
    """Test the corrected weight calculation formulas."""
    
    def test_real_world_example_from_database(self):
        """Test with actual data from the database that showed the bug."""
        # Data from session 5f6883cd-c7b8-4ca8-9615-6758fcd4bac9
        bruto_in = 7400  # kg - truck arrives with fruit
        bruto_out = 680  # kg - truck leaves empty
        container_weight = 296  # kg - known container weight
        
        # Calculate using corrected formulas
        truck_tara = calculate_truck_tara(bruto_in, bruto_out, container_weight)
        neto = calculate_net_weight(bruto_in, bruto_out, container_weight)
        
        # Verify correct calculations
        assert truck_tara == 384, f"Expected truck_tara=384, got {truck_tara}"
        assert neto == 6720, f"Expected neto=6720, got {neto}"
        
        # Verify the business formula: IN = OUT + FRUIT
        assert bruto_in == bruto_out + neto, "Business formula validation failed"
        
        # Verify truck weight calculation: OUT = TRUCK + CONTAINERS
        assert bruto_out == truck_tara + container_weight, "Truck weight validation failed"
    
    def test_multiple_containers(self):
        """Test with multiple containers."""
        bruto_in = 15000  # kg
        bruto_out = 8000  # kg
        container_weights = [300, 250, 280, 320]  # Total: 1150 kg
        total_container_weight = sum(container_weights)
        
        truck_tara = calculate_truck_tara(bruto_in, bruto_out, total_container_weight)
        neto = calculate_net_weight(bruto_in, bruto_out, total_container_weight)
        
        # Expected values
        expected_truck_tara = 8000 - 1150  # 6850 kg
        expected_neto = 15000 - 8000  # 7000 kg
        
        assert truck_tara == expected_truck_tara
        assert neto == expected_neto
        
        # Verify complete weight breakdown
        assert bruto_in == truck_tara + total_container_weight + neto
    
    def test_edge_case_no_containers(self):
        """Test when there are no containers (container weight = 0)."""
        bruto_in = 5000
        bruto_out = 3000
        container_weight = 0
        
        truck_tara = calculate_truck_tara(bruto_in, bruto_out, container_weight)
        neto = calculate_net_weight(bruto_in, bruto_out, container_weight)
        
        # When no containers, truck weight equals OUT weight
        assert truck_tara == bruto_out
        assert neto == 2000  # 5000 - 3000
    
    def test_small_weights(self):
        """Test with small weight values."""
        bruto_in = 500
        bruto_out = 200
        container_weight = 50
        
        truck_tara = calculate_truck_tara(bruto_in, bruto_out, container_weight)
        neto = calculate_net_weight(bruto_in, bruto_out, container_weight)
        
        assert truck_tara == 150  # 200 - 50
        assert neto == 300  # 500 - 200
    
    def test_negative_protection(self):
        """Test that calculations never return negative values."""
        # Scenario where OUT > IN (should not happen in practice)
        bruto_in = 1000
        bruto_out = 2000
        container_weight = 100
        
        truck_tara = calculate_truck_tara(bruto_in, bruto_out, container_weight)
        neto = calculate_net_weight(bruto_in, bruto_out, container_weight)
        
        # Should return 0 instead of negative
        assert truck_tara >= 0
        assert neto == 0  # max(0, 1000 - 2000) = 0
    
    def test_business_logic_validation(self):
        """Test complete business logic with various scenarios."""
        test_cases = [
            # (bruto_in, bruto_out, container_weight, expected_truck, expected_fruit)
            (10000, 3000, 500, 2500, 7000),  # Standard case
            (8500, 2500, 800, 1700, 6000),   # Different values
            (20000, 8000, 2000, 6000, 12000),  # Large weights
            (1500, 800, 200, 600, 700),      # Small weights
        ]
        
        for bruto_in, bruto_out, container_weight, expected_truck, expected_fruit in test_cases:
            truck_tara = calculate_truck_tara(bruto_in, bruto_out, container_weight)
            neto = calculate_net_weight(bruto_in, bruto_out, container_weight)
            
            assert truck_tara == expected_truck, f"Failed for case {bruto_in}, {bruto_out}, {container_weight}"
            assert neto == expected_fruit, f"Failed for case {bruto_in}, {bruto_out}, {container_weight}"
            
            # Validate the complete equation
            assert bruto_in == truck_tara + container_weight + neto, "Complete equation validation failed"


class TestMathematicalProofs:
    """Mathematical proofs that the calculations are correct."""
    
    def test_mathematical_proof_of_formulas(self):
        """Prove the mathematical correctness of the formulas."""
        # Given values
        bruto_in = 10000
        bruto_out = 4000
        container_weight = 1000
        
        # Calculate using our formulas
        truck_tara = calculate_truck_tara(bruto_in, bruto_out, container_weight)
        neto = calculate_net_weight(bruto_in, bruto_out, container_weight)
        
        # Mathematical proofs:
        # 1. OUT weight consists of truck + containers (no fruit)
        assert bruto_out == truck_tara + container_weight
        
        # 2. IN weight consists of truck + containers + fruit
        assert bruto_in == truck_tara + container_weight + neto
        
        # 3. The difference between IN and OUT is the fruit weight
        assert bruto_in - bruto_out == neto
        
        # 4. Substitution proof
        # If: truck_tara = bruto_out - container_weight
        # And: neto = bruto_in - bruto_out
        # Then: bruto_in = truck_tara + container_weight + neto
        #       bruto_in = (bruto_out - container_weight) + container_weight + (bruto_in - bruto_out)
        #       bruto_in = bruto_out - container_weight + container_weight + bruto_in - bruto_out
        #       bruto_in = bruto_in ✓
        
        # This proves our formulas are mathematically correct
    
    def test_all_database_examples(self):
        """Test with all examples from the database analysis."""
        database_examples = [
            # session_id, bruto_in, bruto_out, container_weight
            ("5f6883cd", 7400, 680, 296),
            ("6e058084", 7500, 3200, 273),  # Assuming C-73281 weight
            ("cf2ba484", 9200, 4100, 296),   # C-35434 again
        ]
        
        for session_id, bruto_in, bruto_out, container_weight in database_examples:
            truck_tara = calculate_truck_tara(bruto_in, bruto_out, container_weight)
            neto = calculate_net_weight(bruto_in, bruto_out, container_weight)
            
            # The fruit weight should always be IN - OUT
            expected_neto = bruto_in - bruto_out
            assert neto == expected_neto, f"Session {session_id}: Expected {expected_neto}, got {neto}"
            
            # The truck weight should always be OUT - containers
            expected_truck = bruto_out - container_weight
            assert truck_tara == expected_truck, f"Session {session_id}: Expected {expected_truck}, got {truck_tara}"
            
            # Complete validation
            assert bruto_in == truck_tara + container_weight + neto, f"Session {session_id}: Complete formula failed"


if __name__ == "__main__":
    # Run tests directly
    test = TestCorrectedWeightCalculations()
    test.test_real_world_example_from_database()
    test.test_multiple_containers()
    test.test_business_logic_validation()
    
    proof = TestMathematicalProofs()
    proof.test_mathematical_proof_of_formulas()
    
    print("✅ All weight calculation tests passed!")
    print("\nCorrected formulas:")
    print("- Truck weight = OUT weight - Container weights")
    print("- Fruit weight = IN weight - OUT weight")
    print("\nThis ensures accurate business calculations for billing and inventory.")