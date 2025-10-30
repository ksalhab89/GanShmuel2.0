"""Core weighing business logic service."""

import uuid
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.repositories import ContainerRepository, SessionRepository, TransactionRepository
from ..models.schemas import WeightRequest, WeightResponse
from ..utils.calculations import (
    calculate_net_weight,
    calculate_truck_tara,
    normalize_weight_to_kg,
    parse_container_list,
    validate_weight_range,
)


class WeighingSequenceError(Exception):
    """Exception raised for invalid weighing sequences."""
    pass


class InvalidWeightError(Exception):
    """Exception raised for invalid weight values."""
    pass


class ContainerNotFoundError(Exception):
    """Exception raised when containers are not registered."""
    pass


class WeightService:
    """Core weighing business logic service."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.container_repo = ContainerRepository(session)
        self.transaction_repo = TransactionRepository(session)
        self.session_repo = SessionRepository(session)
    
    async def record_weight(self, request: WeightRequest) -> Tuple[WeightResponse, Optional[str]]:
        """
        Main weighing operation handler.
        
        Args:
            request: Weight recording request
            
        Returns:
            Tuple of (WeightResponse, error_message)
            
        Raises:
            WeighingSequenceError: Invalid weighing sequence
            InvalidWeightError: Invalid weight values
            ContainerNotFoundError: Unknown containers
        """
        # Validate weight value
        if not validate_weight_range(request.weight, request.unit):
            raise InvalidWeightError(f"Weight {request.weight} {request.unit} is out of valid range")
        
        # Parse container list
        container_ids = parse_container_list(request.containers)
        if not container_ids:
            raise InvalidWeightError("Container list cannot be empty")
        
        # Validate weighing sequence and containers
        await self._validate_weighing_sequence(request, container_ids)
        
        # Create transaction based on direction
        if request.direction == "in":
            return await self._handle_in_direction(request, container_ids)
        elif request.direction == "out":
            return await self._handle_out_direction(request, container_ids)
        else:  # direction == "none"
            return await self._handle_none_direction(request, container_ids)
    
    async def _validate_weighing_sequence(self, request: WeightRequest, container_ids: List[str]) -> None:
        """
        Validate weighing sequence business rules.
        
        Args:
            request: Weight recording request
            container_ids: Parsed container IDs
            
        Raises:
            WeighingSequenceError: Invalid sequence
            ContainerNotFoundError: Unknown containers
        """
        if request.direction == "out":
            # For OUT, must have matching IN transaction
            matching_in = await self.transaction_repo.find_matching_in_transaction(
                request.truck if request.truck != "na" else None, 
                container_ids
            )
            if not matching_in and not request.force:
                raise WeighingSequenceError(
                    f"No matching IN transaction found for truck={request.truck}, containers={container_ids}"
                )
            
            # Check if containers are registered for weight calculation
            container_info = await self.container_repo.get_container_weight_info(container_ids)
            unknown_containers = [info.container_id for info in container_info if not info.is_known]
            if unknown_containers:
                raise ContainerNotFoundError(
                    f"Unknown container weights for calculation: {', '.join(unknown_containers)}"
                )
        
        elif request.direction == "in":
            # For IN, check if already exists (unless force=True)
            if not request.force:
                existing_in = await self.transaction_repo.find_matching_in_transaction(
                    request.truck if request.truck != "na" else None,
                    container_ids
                )
                if existing_in:
                    raise WeighingSequenceError(
                        f"IN transaction already exists for truck={request.truck}, containers={container_ids}"
                    )
    
    async def _handle_in_direction(self, request: WeightRequest, container_ids: List[str]) -> Tuple[WeightResponse, Optional[str]]:
        """
        Handle IN direction weighing.
        
        Args:
            request: Weight request
            container_ids: Container IDs
            
        Returns:
            Tuple of (WeightResponse, error_message)
        """
        # Generate new session ID
        session_id = str(uuid.uuid4())
        
        # Normalize weight to kg
        bruto_kg = normalize_weight_to_kg(request.weight, request.unit)

        # Create IN transaction
        _transaction = await self.transaction_repo.create(
            session_id=session_id,
            direction="in",
            truck=request.truck if request.truck != "na" else None,
            containers=container_ids,
            bruto=bruto_kg,
            produce=request.produce if request.produce != "na" else None
        )

        await self.session.commit()
        
        # Return response
        return WeightResponse(
            id=session_id,
            session_id=session_id,
            direction="in",
            truck=request.truck,
            bruto=bruto_kg,
            gross_weight=bruto_kg,
            truck_tara=None,
            neto="na",
            net_weight="na"
        ), None
    
    async def _handle_out_direction(self, request: WeightRequest, container_ids: List[str]) -> Tuple[WeightResponse, Optional[str]]:
        """
        Handle OUT direction weighing with weight calculations.
        
        Args:
            request: Weight request
            container_ids: Container IDs
            
        Returns:
            Tuple of (WeightResponse, error_message)
        """
        # Find matching IN transaction
        matching_in = await self.transaction_repo.find_matching_in_transaction(
            request.truck if request.truck != "na" else None,
            container_ids
        )
        
        if not matching_in:
            if request.force:
                # Create standalone OUT transaction
                return await self._create_standalone_out_transaction(request, container_ids)
            else:
                raise WeighingSequenceError("No matching IN transaction found")
        
        # Get container weights for calculation
        container_info = await self.container_repo.get_container_weight_info(container_ids)
        container_weights_kg = [info.weight_in_kg for info in container_info if info.weight_in_kg is not None]
        
        # Normalize OUT weight to kg
        bruto_out_kg = normalize_weight_to_kg(request.weight, request.unit)
        
        # Calculate weights using corrected business formula
        total_container_tara = sum(container_weights_kg)
        truck_tara = calculate_truck_tara(matching_in.bruto, bruto_out_kg, total_container_tara)
        neto = calculate_net_weight(matching_in.bruto, bruto_out_kg, total_container_tara)
        
        # Update IN transaction with calculated values
        await self.transaction_repo.update_out_transaction(matching_in, truck_tara, neto)
        
        # Create OUT transaction
        out_transaction = await self.transaction_repo.create(
            session_id=matching_in.session_id,
            direction="out",
            truck=request.truck if request.truck != "na" else None,
            containers=container_ids,
            bruto=bruto_out_kg,
            produce=request.produce if request.produce != "na" else None
        )
        
        # Update OUT transaction with calculated values
        await self.transaction_repo.update_out_transaction(out_transaction, truck_tara, neto)
        
        await self.session.commit()
        
        return WeightResponse(
            id=matching_in.session_id,
            session_id=matching_in.session_id,
            direction="out",
            truck=request.truck,
            bruto=bruto_out_kg,
            gross_weight=bruto_out_kg,
            truck_tara=truck_tara,
            neto=neto if isinstance(neto, int) else "na",
            net_weight=neto if isinstance(neto, int) else "na"
        ), None
    
    async def _handle_none_direction(self, request: WeightRequest, container_ids: List[str]) -> Tuple[WeightResponse, Optional[str]]:
        """
        Handle NONE direction weighing (standalone weighing).
        
        Args:
            request: Weight request
            container_ids: Container IDs
            
        Returns:
            Tuple of (WeightResponse, error_message)
        """
        # Generate new session ID
        session_id = str(uuid.uuid4())
        
        # Normalize weight to kg
        bruto_kg = normalize_weight_to_kg(request.weight, request.unit)

        # Create NONE transaction
        _transaction = await self.transaction_repo.create(
            session_id=session_id,
            direction="none",
            truck=request.truck if request.truck != "na" else None,
            containers=container_ids,
            bruto=bruto_kg,
            produce=request.produce if request.produce != "na" else None
        )

        await self.session.commit()
        
        return WeightResponse(
            id=session_id,
            session_id=session_id,
            direction="none",
            truck=request.truck,
            bruto=bruto_kg,
            gross_weight=bruto_kg,
            truck_tara=None,
            neto="na",  # NONE transactions don't calculate net weight
            net_weight="na"
        ), None
    
    async def _create_standalone_out_transaction(self, request: WeightRequest, container_ids: List[str]) -> Tuple[WeightResponse, Optional[str]]:
        """
        Create standalone OUT transaction when force=True and no matching IN.
        
        Args:
            request: Weight request
            container_ids: Container IDs
            
        Returns:
            Tuple of (WeightResponse, error_message)
        """
        # Generate new session ID
        session_id = str(uuid.uuid4())
        
        # Normalize weight to kg
        bruto_kg = normalize_weight_to_kg(request.weight, request.unit)

        # Create OUT transaction without calculations
        _transaction = await self.transaction_repo.create(
            session_id=session_id,
            direction="out",
            truck=request.truck if request.truck != "na" else None,
            containers=container_ids,
            bruto=bruto_kg,
            produce=request.produce if request.produce != "na" else None
        )

        await self.session.commit()
        
        return WeightResponse(
            id=session_id,
            session_id=session_id,
            direction="out",
            truck=request.truck,
            bruto=bruto_kg,
            gross_weight=bruto_kg,
            truck_tara=None,
            neto="na",  # Cannot calculate without IN transaction
            net_weight="na"
        ), None
    
    async def generate_session(self) -> str:
        """
        Generate a new session ID.
        
        Returns:
            New UUID session ID
        """
        return str(uuid.uuid4())
    
    async def validate_weighing_sequence(self, 
                                       direction: str, 
                                       truck: Optional[str], 
                                       containers: List[str],
                                       force: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Validate weighing sequence without creating transaction.
        
        Args:
            direction: Weighing direction
            truck: Truck license
            containers: Container IDs
            force: Force flag
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if direction == "out":
                matching_in = await self.transaction_repo.find_matching_in_transaction(
                    truck if truck != "na" else None,
                    containers
                )
                if not matching_in and not force:
                    return False, "No matching IN transaction found"
                
                # Check container weights
                container_info = await self.container_repo.get_container_weight_info(containers)
                unknown_containers = [info.container_id for info in container_info if not info.is_known]
                if unknown_containers:
                    return False, f"Unknown container weights: {', '.join(unknown_containers)}"
            
            elif direction == "in" and not force:
                existing_in = await self.transaction_repo.find_matching_in_transaction(
                    truck if truck != "na" else None,
                    containers
                )
                if existing_in:
                    return False, "IN transaction already exists"
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    async def calculate_net_weight(self,
                                 bruto_in: int,
                                 bruto_out: int,
                                 container_ids: List[str]) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        """
        Calculate net weight for given parameters.
        
        Args:
            bruto_in: IN gross weight (kg)
            bruto_out: OUT gross weight (kg)
            container_ids: Container IDs
            
        Returns:
            Tuple of (truck_tara, neto, error_message)
        """
        try:
            # Get container weights
            container_info = await self.container_repo.get_container_weight_info(container_ids)
            unknown_containers = [info.container_id for info in container_info if not info.is_known]
            
            if unknown_containers:
                return None, None, f"Unknown container weights: {', '.join(unknown_containers)}"
            
            container_weights_kg = [info.weight_in_kg for info in container_info if info.weight_in_kg is not None]
            
            # Calculate weights using corrected formulas
            total_container_tara = sum(container_weights_kg)
            truck_tara = calculate_truck_tara(bruto_in, bruto_out, total_container_tara)
            neto = calculate_net_weight(bruto_in, bruto_out, total_container_tara)
            
            return truck_tara, neto, None
            
        except Exception as e:
            return None, None, str(e)