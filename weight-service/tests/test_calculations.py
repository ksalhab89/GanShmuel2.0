"""Tests for weight calculation utilities."""

import pytest
import json
from src.utils.calculations import (
    lbs_to_kg,
    kg_to_lbs,
    normalize_weight_to_kg,
    convert_weight,
    parse_container_list,
    validate_container_ids,
    containers_to_json,
    containers_from_json,
    calculate_net_weight,
    calculate_truck_tara,
    get_container_weights,
    validate_weight_calculation,
    can_calculate_net_weight,
    get_weight_summary,
    validate_weight_range,
)
from src.models.database import ContainerRegistered


class TestWeightConversions:
    """Test weight conversion functions."""

    def test_lbs_to_kg(self):
        """Test pounds to kilograms conversion."""
        assert lbs_to_kg(100) == 45
        assert lbs_to_kg(220) == 99

    def test_kg_to_lbs(self):
        """Test kilograms to pounds conversion."""
        assert kg_to_lbs(100) == 220
        assert kg_to_lbs(45) == 99

    def test_normalize_weight_to_kg_from_lbs(self):
        """Test normalizing lbs to kg."""
        assert normalize_weight_to_kg(220, "lbs") == 99

    def test_normalize_weight_to_kg_already_kg(self):
        """Test normalizing kg (no conversion)."""
        assert normalize_weight_to_kg(100, "kg") == 100

    def test_convert_weight_same_unit(self):
        """Test converting weight when units are the same."""
        assert convert_weight(100, "kg", "kg") == 100
        assert convert_weight(100, "lbs", "lbs") == 100

    def test_convert_weight_lbs_to_kg(self):
        """Test converting lbs to kg."""
        assert convert_weight(220, "lbs", "kg") == 99

    def test_convert_weight_kg_to_lbs(self):
        """Test converting kg to lbs."""
        assert convert_weight(100, "kg", "lbs") == 220

    def test_convert_weight_invalid_units(self):
        """Test converting with invalid unit raises ValueError."""
        with pytest.raises(ValueError, match="Invalid unit conversion"):
            convert_weight(100, "grams", "kg")


class TestContainerParsing:
    """Test container parsing functions."""

    def test_parse_container_list(self):
        """Test parsing comma-separated containers."""
        result = parse_container_list("C001,C002,C003")
        assert result == ["C001", "C002", "C003"]

    def test_parse_container_list_with_whitespace(self):
        """Test parsing with extra whitespace."""
        result = parse_container_list(" C001 , C002 , C003 ")
        assert result == ["C001", "C002", "C003"]

    def test_validate_container_ids_valid(self):
        """Test validation with valid IDs."""
        is_valid, errors = validate_container_ids(["C001", "C002"])
        assert is_valid
        assert errors == []

    def test_validate_container_ids_too_long(self):
        """Test validation with ID too long."""
        is_valid, errors = validate_container_ids(["C" * 20])
        assert not is_valid
        assert "exceeds 15 characters" in errors[0]

    def test_validate_container_ids_invalid_chars(self):
        """Test validation with invalid characters."""
        is_valid, errors = validate_container_ids(["C@#$%"])
        assert not is_valid
        assert "invalid characters" in errors[0]

    def test_containers_to_json(self):
        """Test converting container list to JSON."""
        result = containers_to_json(["C001", "C002"])
        assert result == '["C001", "C002"]'

    def test_containers_from_json_valid(self):
        """Test parsing valid JSON."""
        result = containers_from_json('["C001", "C002"]')
        assert result == ["C001", "C002"]

    def test_containers_from_json_invalid(self):
        """Test parsing invalid JSON returns empty list."""
        result = containers_from_json("not valid json")
        assert result == []

    def test_containers_from_json_none(self):
        """Test parsing None returns empty list."""
        result = containers_from_json(None)
        assert result == []


class TestWeightCalculations:
    """Test weight calculation functions."""

    def test_calculate_net_weight(self):
        """Test net weight calculation."""
        # IN: 10000kg, OUT: 4000kg -> Net: 6000kg
        assert calculate_net_weight(10000, 4000, 500) == 6000

    def test_calculate_net_weight_negative_result(self):
        """Test net weight with negative result returns 0."""
        assert calculate_net_weight(3000, 5000, 500) == 0

    def test_calculate_truck_tara(self):
        """Test truck tara calculation."""
        # OUT: 4000kg, Containers: 500kg -> Truck: 3500kg
        assert calculate_truck_tara(10000, 4000, 500) == 3500

    def test_calculate_truck_tara_negative_result(self):
        """Test truck tara with negative result returns 0."""
        assert calculate_truck_tara(10000, 300, 500) == 0


class TestContainerWeights:
    """Test container weight functions."""

    def test_get_container_weights_all_known(self):
        """Test getting weights for all known containers."""
        registry = {
            "C001": ContainerRegistered(container_id="C001", weight=500, unit="kg"),
            "C002": ContainerRegistered(container_id="C002", weight=600, unit="kg"),
        }
        weights, unknown = get_container_weights(["C001", "C002"], registry)
        assert weights == [500, 600]
        assert unknown == []

    def test_get_container_weights_some_unknown(self):
        """Test getting weights with unknown containers."""
        registry = {
            "C001": ContainerRegistered(container_id="C001", weight=500, unit="kg"),
        }
        weights, unknown = get_container_weights(["C001", "C999"], registry)
        assert weights == [500]
        assert "C999" in unknown

    def test_get_container_weights_with_null_weight(self):
        """Test getting weights when container has null weight."""
        registry = {
            "C001": ContainerRegistered(container_id="C001", weight=None, unit="kg"),
        }
        weights, unknown = get_container_weights(["C001"], registry)
        assert weights == []
        assert "C001" in unknown

    def test_get_container_weights_all_unknown(self):
        """Test getting weights when all containers unknown."""
        registry = {}
        weights, unknown = get_container_weights(["C001", "C002"], registry)
        assert weights == []
        assert unknown == ["C001", "C002"]


class TestWeightValidation:
    """Test weight validation functions."""

    def test_validate_weight_calculation_valid(self):
        """Test validation with valid weights."""
        is_valid, error = validate_weight_calculation(10000, 3500, [500, 600])
        assert is_valid
        assert error is None

    def test_validate_weight_calculation_zero_bruto(self):
        """Test validation with zero gross weight."""
        is_valid, error = validate_weight_calculation(0, 3500, [500])
        assert not is_valid
        assert "must be positive" in error

    def test_validate_weight_calculation_negative_truck_tara(self):
        """Test validation with negative truck tara."""
        is_valid, error = validate_weight_calculation(10000, -100, [500])
        assert not is_valid
        assert "cannot be negative" in error

    def test_validate_weight_calculation_negative_container_weight(self):
        """Test validation with negative container weight."""
        is_valid, error = validate_weight_calculation(10000, 3500, [500, -100])
        assert not is_valid
        assert "cannot be negative" in error

    def test_validate_weight_calculation_tara_exceeds_bruto(self):
        """Test validation when tara exceeds gross weight."""
        is_valid, error = validate_weight_calculation(1000, 3500, [500, 600])
        assert not is_valid
        assert "exceeds gross weight" in error


class TestBusinessLogicUtilities:
    """Test business logic utility functions."""

    def test_can_calculate_net_weight_all_known(self):
        """Test checking if net weight can be calculated."""
        registry = {
            "C001": ContainerRegistered(container_id="C001", weight=500, unit="kg"),
            "C002": ContainerRegistered(container_id="C002", weight=600, unit="kg"),
        }
        can_calculate, missing = can_calculate_net_weight(["C001", "C002"], registry)
        assert can_calculate
        assert missing == []

    def test_can_calculate_net_weight_with_unknowns(self):
        """Test checking calculation with unknown containers."""
        registry = {
            "C001": ContainerRegistered(container_id="C001", weight=500, unit="kg"),
        }
        can_calculate, missing = can_calculate_net_weight(["C001", "C999"], registry)
        assert not can_calculate
        assert "C999" in missing

    def test_get_weight_summary(self):
        """Test getting weight summary."""
        summary = get_weight_summary(10000, 3500, [500, 600])
        assert summary["bruto"] == 10000
        assert summary["truck_tara"] == 3500
        assert summary["container_tara_total"] == 1100
        assert summary["total_tara"] == 4600
        assert summary["neto"] == 5400

    def test_get_weight_summary_no_truck_tara(self):
        """Test weight summary with no truck tara."""
        summary = get_weight_summary(10000, None, [500, 600])
        assert summary["truck_tara"] == 0
        assert summary["container_tara_total"] == 1100
        assert summary["total_tara"] == 1100
        assert summary["neto"] == 8900

    def test_get_weight_summary_tara_exceeds_bruto(self):
        """Test weight summary when tara exceeds bruto."""
        summary = get_weight_summary(1000, 900, [200])
        assert summary["neto"] == 0  # Clamped to 0

    def test_validate_weight_range_valid(self):
        """Test validating weight in valid range."""
        assert validate_weight_range(5000, "kg") is True

    def test_validate_weight_range_too_small(self):
        """Test validating weight below minimum."""
        assert validate_weight_range(0, "kg") is False

    def test_validate_weight_range_too_large(self):
        """Test validating weight above maximum."""
        assert validate_weight_range(200000, "kg") is False
