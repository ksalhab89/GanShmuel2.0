"""Weight calculation utilities for the Weight Service V2."""

import json
from typing import Dict, List, Optional, Tuple

from ..models.database import ContainerRegistered


# ============================================================================
# Weight Conversion Functions
# ============================================================================

def lbs_to_kg(weight_lbs: float) -> int:
    """Convert pounds to kilograms.
    
    Args:
        weight_lbs: Weight in pounds
        
    Returns:
        Weight in kilograms (rounded to nearest integer)
    """
    return int(weight_lbs * 0.453592)


def kg_to_lbs(weight_kg: float) -> int:
    """Convert kilograms to pounds.
    
    Args:
        weight_kg: Weight in kilograms
        
    Returns:
        Weight in pounds (rounded to nearest integer)
    """
    return int(weight_kg / 0.453592)


def normalize_weight_to_kg(weight: int, unit: str) -> int:
    """Normalize weight value to kilograms.
    
    Args:
        weight: Weight value
        unit: Unit of measurement ('kg' or 'lbs')
        
    Returns:
        Weight in kilograms
    """
    if unit == "lbs":
        return lbs_to_kg(weight)
    return weight


def convert_weight(weight: int, from_unit: str, to_unit: str) -> int:
    """Convert weight between units.
    
    Args:
        weight: Weight value
        from_unit: Source unit ('kg' or 'lbs')
        to_unit: Target unit ('kg' or 'lbs')
        
    Returns:
        Converted weight value
    """
    if from_unit == to_unit:
        return weight
    
    if from_unit == "lbs" and to_unit == "kg":
        return lbs_to_kg(weight)
    elif from_unit == "kg" and to_unit == "lbs":
        return kg_to_lbs(weight)
    else:
        raise ValueError(f"Invalid unit conversion: {from_unit} to {to_unit}")


# ============================================================================
# Container Parsing Functions
# ============================================================================

def parse_container_list(containers_str: str) -> List[str]:
    """Parse comma-separated container IDs into a list.
    
    Args:
        containers_str: Comma-separated container IDs
        
    Returns:
        List of container IDs (trimmed and filtered)
    """
    return [c.strip() for c in containers_str.split(",") if c.strip()]


def validate_container_ids(container_ids: List[str]) -> Tuple[bool, List[str]]:
    """Validate container ID formats.
    
    Args:
        container_ids: List of container IDs to validate
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    for container_id in container_ids:
        if len(container_id) > 15:
            errors.append(f"Container ID '{container_id}' exceeds 15 characters")
        
        if not container_id.replace("-", "").replace("_", "").isalnum():
            errors.append(f"Container ID '{container_id}' contains invalid characters")
    
    return len(errors) == 0, errors


def containers_to_json(container_ids: List[str]) -> str:
    """Convert container ID list to JSON string for database storage.
    
    Args:
        container_ids: List of container IDs
        
    Returns:
        JSON string representation
    """
    return json.dumps(container_ids)


def containers_from_json(json_str: str) -> List[str]:
    """Parse container IDs from JSON string.
    
    Args:
        json_str: JSON string from database
        
    Returns:
        List of container IDs
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return []


# ============================================================================
# Weight Calculation Functions
# ============================================================================

def calculate_net_weight(
    bruto_in: int,
    bruto_out: int,
    container_tara_sum: int
) -> int:
    """Calculate net fruit weight using the correct formula.
    
    Business Logic:
    - When truck arrives (IN): Total weight = Truck + Containers + Fruit
    - When truck leaves (OUT): Total weight = Truck + Containers (no fruit)
    - Therefore: Net fruit weight = IN weight - OUT weight
    
    Args:
        bruto_in: Gross weight from IN transaction (kg)
        bruto_out: Gross weight from OUT transaction (kg) 
        container_tara_sum: Sum of container tare weights (kg) - not used in net calculation
        
    Returns:
        Net fruit weight in kg
    """
    # The net fruit weight is simply the difference between IN and OUT weights
    # This is because OUT weight includes truck + containers, IN includes truck + containers + fruit
    neto = bruto_in - bruto_out
    return max(0, neto)  # Ensure non-negative result


def calculate_truck_tara(bruto_in: int, bruto_out: int, container_tara_sum: int) -> int:
    """Calculate truck tare weight from OUT weighing.
    
    Business Logic:
    - OUT weight = Truck weight + Container weights (empty truck with empty containers)
    - Therefore: Truck weight = OUT weight - Container weights
    
    Args:
        bruto_in: Gross weight from IN transaction (kg) - not used in truck tara calculation
        bruto_out: Gross weight from OUT transaction (kg)
        container_tara_sum: Sum of container tare weights (kg)
        
    Returns:
        Calculated truck tare weight in kg
    """
    # Truck tare is the OUT weight minus the known container weights
    truck_tara = bruto_out - container_tara_sum
    return max(0, truck_tara)  # Ensure non-negative result


def get_container_weights(
    container_ids: List[str],
    container_registry: Dict[str, ContainerRegistered]
) -> Tuple[List[int], List[str]]:
    """Get container tare weights from registry.
    
    Args:
        container_ids: List of container IDs
        container_registry: Dictionary of container ID to ContainerRegistered
        
    Returns:
        Tuple of (known_weights_in_kg, unknown_container_ids)
    """
    known_weights = []
    unknown_containers = []
    
    for container_id in container_ids:
        if container_id in container_registry:
            container = container_registry[container_id]
            if container.weight is not None:
                weight_kg = container.weight_in_kg
                if weight_kg is not None:
                    known_weights.append(weight_kg)
                else:
                    unknown_containers.append(container_id)
            else:
                unknown_containers.append(container_id)
        else:
            unknown_containers.append(container_id)
    
    return known_weights, unknown_containers


def validate_weight_calculation(
    bruto: int,
    truck_tara: Optional[int],
    container_weights: List[int]
) -> Tuple[bool, Optional[str]]:
    """Validate weight calculation parameters.
    
    Args:
        bruto: Gross weight
        truck_tara: Truck tare weight (optional)
        container_weights: Container tare weights
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if bruto <= 0:
        return False, "Gross weight must be positive"
    
    if truck_tara is not None and truck_tara < 0:
        return False, "Truck tare weight cannot be negative"
    
    if any(w < 0 for w in container_weights):
        return False, "Container weights cannot be negative"
    
    total_tara = (truck_tara or 0) + sum(container_weights)
    if total_tara >= bruto:
        return False, "Total tare weight exceeds gross weight"
    
    return True, None


# ============================================================================
# Business Logic Utilities
# ============================================================================

def can_calculate_net_weight(
    container_ids: List[str],
    container_registry: Dict[str, ContainerRegistered]
) -> Tuple[bool, List[str]]:
    """Check if net weight can be calculated for given containers.
    
    Args:
        container_ids: List of container IDs
        container_registry: Dictionary of container registry
        
    Returns:
        Tuple of (can_calculate, missing_container_ids)
    """
    _, unknown_containers = get_container_weights(container_ids, container_registry)
    return len(unknown_containers) == 0, unknown_containers


def get_weight_summary(
    bruto: int,
    truck_tara: Optional[int],
    container_weights: List[int]
) -> Dict[str, int]:
    """Get weight calculation summary.
    
    Args:
        bruto: Gross weight
        truck_tara: Truck tare weight
        container_weights: Container tare weights
        
    Returns:
        Dictionary with weight breakdown
    """
    total_container_tara = sum(container_weights)
    truck_weight = truck_tara or 0
    total_tara = truck_weight + total_container_tara
    neto = max(0, bruto - total_tara)
    
    return {
        "bruto": bruto,
        "truck_tara": truck_weight,
        "container_tara_total": total_container_tara,
        "total_tara": total_tara,
        "neto": neto
    }


def validate_weight_range(weight: int, unit: str = "kg") -> bool:
    """Validate if weight is within reasonable range.
    
    Args:
        weight: Weight value
        unit: Weight unit
        
    Returns:
        True if weight is within reasonable range
    """
    # Convert to kg for validation
    weight_kg = normalize_weight_to_kg(weight, unit)
    
    # Reasonable range: 1kg to 100,000kg (100 tons)
    return 1 <= weight_kg <= 100_000