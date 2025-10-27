"""Container weight management service."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import ContainerRegistered
from ..models.repositories import ContainerRepository
from ..models.schemas import ContainerWeightData, ContainerWeightInfo
from ..utils.calculations import normalize_weight_to_kg, validate_weight_range


class ContainerValidationError(Exception):
    """Exception raised for container validation errors."""
    pass


class DuplicateContainerError(Exception):
    """Exception raised for duplicate container registration."""
    pass


class ContainerService:
    """Container weight management service."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.container_repo = ContainerRepository(session)
    
    async def register_container(self, 
                               container_id: str, 
                               weight: int, 
                               unit: str = "kg",
                               allow_update: bool = False) -> Tuple[ContainerRegistered, bool]:
        """
        Register a single container with its tare weight.
        
        Args:
            container_id: Container identifier
            weight: Container tare weight
            unit: Weight unit ('kg' or 'lbs')
            allow_update: Whether to update existing container
            
        Returns:
            Tuple of (ContainerRegistered, was_updated)
            
        Raises:
            ContainerValidationError: Invalid container data
            DuplicateContainerError: Container already exists
        """
        # Validate container ID
        self._validate_container_id(container_id)
        
        # Validate weight
        if not validate_weight_range(weight, unit):
            raise ContainerValidationError(f"Weight {weight} {unit} is out of valid range")
        
        # Normalize weight to kg
        weight_kg = normalize_weight_to_kg(weight, unit)
        
        # Check if container already exists
        existing = await self.container_repo.get_by_id(container_id)
        if existing and not allow_update:
            raise DuplicateContainerError(f"Container {container_id} already registered")
        
        if existing and allow_update:
            # Update existing container
            updated_container = await self.container_repo.update_weight(container_id, weight_kg, "kg")
            await self.session.commit()
            return updated_container, True
        else:
            # Create new container
            new_container = await self.container_repo.create(container_id, weight_kg, "kg")
            await self.session.commit()
            return new_container, False
    
    async def batch_register_containers(self, 
                                      containers: List[ContainerWeightData],
                                      allow_updates: bool = True,
                                      skip_duplicates: bool = False) -> Dict[str, any]:
        """
        Register multiple containers in batch operation.
        
        Args:
            containers: List of container weight data
            allow_updates: Whether to allow updating existing containers
            skip_duplicates: Whether to skip duplicate containers
            
        Returns:
            Dictionary with batch operation results
        """
        results = {
            "processed": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
            "successful_containers": [],
            "failed_containers": []
        }
        
        for container_data in containers:
            try:
                # Validate container data
                self._validate_container_data(container_data)
                
                # Check if container exists
                existing = await self.container_repo.get_by_id(container_data.id)
                
                if existing:
                    if allow_updates:
                        # Update existing container
                        weight_kg = normalize_weight_to_kg(container_data.weight, container_data.unit)
                        await self.container_repo.update_weight(container_data.id, weight_kg, "kg")
                        results["updated"] += 1
                        results["successful_containers"].append(container_data.id)
                    elif skip_duplicates:
                        # Skip duplicate
                        results["skipped"] += 1
                    else:
                        raise DuplicateContainerError(f"Container {container_data.id} already exists")
                else:
                    # Create new container
                    weight_kg = normalize_weight_to_kg(container_data.weight, container_data.unit)
                    await self.container_repo.create(container_data.id, weight_kg, "kg")
                    results["processed"] += 1
                    results["successful_containers"].append(container_data.id)
                
            except Exception as e:
                error_msg = f"Container {container_data.id}: {str(e)}"
                results["errors"].append(error_msg)
                results["failed_containers"].append(container_data.id)
        
        # Commit all changes
        if results["processed"] > 0 or results["updated"] > 0:
            await self.session.commit()
        
        return results
    
    async def get_container_weight(self, container_id: str) -> Optional[ContainerWeightInfo]:
        """
        Get container tare weight information.
        
        Args:
            container_id: Container identifier
            
        Returns:
            ContainerWeightInfo or None if not found
        """
        container = await self.container_repo.get_by_id(container_id)
        
        if not container:
            return ContainerWeightInfo(
                container_id=container_id,
                weight=None,
                unit="kg",
                is_known=False
            )
        
        return ContainerWeightInfo(
            container_id=container_id,
            weight=container.weight,
            unit=container.unit,
            is_known=container.weight is not None
        )
    
    async def get_multiple_container_weights(self, container_ids: List[str]) -> List[ContainerWeightInfo]:
        """
        Get weight information for multiple containers.
        
        Args:
            container_ids: List of container identifiers
            
        Returns:
            List of ContainerWeightInfo objects
        """
        return await self.container_repo.get_container_weight_info(container_ids)
    
    async def update_container_weight(self, 
                                    container_id: str, 
                                    weight: int, 
                                    unit: str = "kg") -> Optional[ContainerRegistered]:
        """
        Update existing container weight.
        
        Args:
            container_id: Container identifier
            weight: New weight value
            unit: Weight unit
            
        Returns:
            Updated ContainerRegistered or None if not found
            
        Raises:
            ContainerValidationError: Invalid container data
        """
        # Validate inputs
        self._validate_container_id(container_id)
        
        if not validate_weight_range(weight, unit):
            raise ContainerValidationError(f"Weight {weight} {unit} is out of valid range")
        
        # Normalize weight to kg
        weight_kg = normalize_weight_to_kg(weight, unit)
        
        # Update container
        updated_container = await self.container_repo.update_weight(container_id, weight_kg, "kg")
        
        if updated_container:
            await self.session.commit()
        
        return updated_container
    
    async def find_unknown_containers(self, 
                                    from_time: Optional[datetime] = None,
                                    to_time: Optional[datetime] = None) -> List[str]:
        """
        Find containers with unknown weights used in transactions.
        
        Args:
            from_time: Start time filter
            to_time: End time filter
            
        Returns:
            List of container IDs with unknown weights
        """
        return await self.container_repo.get_unknown_containers(from_time, to_time)
    
    async def get_all_registered_containers(self) -> List[ContainerRegistered]:
        """
        Get all containers with known weights.
        
        Returns:
            List of registered containers
        """
        return await self.container_repo.get_all_with_weights()
    
    async def validate_containers_for_weighing(self, container_ids: List[str]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate containers for weighing operation.
        
        Args:
            container_ids: List of container IDs to validate
            
        Returns:
            Tuple of (all_known, known_containers, unknown_containers)
        """
        container_info = await self.container_repo.get_container_weight_info(container_ids)
        
        known_containers = [info.container_id for info in container_info if info.is_known]
        unknown_containers = [info.container_id for info in container_info if not info.is_known]
        
        return len(unknown_containers) == 0, known_containers, unknown_containers
    
    async def get_container_total_tare(self, container_ids: List[str]) -> Tuple[Optional[int], List[str]]:
        """
        Calculate total tare weight for container list.
        
        Args:
            container_ids: List of container IDs
            
        Returns:
            Tuple of (total_tare_kg, unknown_containers)
        """
        container_info = await self.container_repo.get_container_weight_info(container_ids)
        
        unknown_containers = [info.container_id for info in container_info if not info.is_known]
        if unknown_containers:
            return None, unknown_containers
        
        # Sum all known weights in kg
        total_tare = sum(info.weight_in_kg for info in container_info if info.weight_in_kg is not None)
        
        return total_tare, []
    
    async def delete_container(self, container_id: str) -> bool:
        """
        Delete container registration.
        
        Args:
            container_id: Container identifier
            
        Returns:
            True if deleted, False if not found
        """
        container = await self.container_repo.get_by_id(container_id)
        if container:
            await self.session.delete(container)
            await self.session.commit()
            return True
        return False
    
    async def get_container_usage_stats(self, 
                                      container_id: str,
                                      from_time: Optional[datetime] = None,
                                      to_time: Optional[datetime] = None) -> Dict[str, any]:
        """
        Get usage statistics for a container.
        
        Args:
            container_id: Container identifier
            from_time: Start time filter
            to_time: End time filter
            
        Returns:
            Dictionary with usage statistics
        """
        # Get sessions using this container
        from ..models.repositories import TransactionRepository
        transaction_repo = TransactionRepository(self.session)
        
        session_ids = await transaction_repo.get_sessions_with_container(
            container_id, from_time, to_time
        )
        
        # Get container info
        container_info = await self.get_container_weight(container_id)
        
        return {
            "container_id": container_id,
            "is_registered": container_info.is_known if container_info else False,
            "weight": container_info.weight if container_info else None,
            "unit": container_info.unit if container_info else "kg",
            "usage_count": len(session_ids),
            "session_ids": session_ids
        }
    
    def _validate_container_id(self, container_id: str) -> None:
        """
        Validate container ID format.
        
        Args:
            container_id: Container identifier
            
        Raises:
            ContainerValidationError: Invalid container ID
        """
        if not container_id or not container_id.strip():
            raise ContainerValidationError("Container ID cannot be empty")
        
        if len(container_id) > 15:
            raise ContainerValidationError(f"Container ID '{container_id}' exceeds 15 characters")
        
        # Allow alphanumeric, hyphens, and underscores
        if not container_id.replace("-", "").replace("_", "").isalnum():
            raise ContainerValidationError(f"Container ID '{container_id}' contains invalid characters")
    
    def _validate_container_data(self, container_data: ContainerWeightData) -> None:
        """
        Validate container weight data.
        
        Args:
            container_data: Container weight data
            
        Raises:
            ContainerValidationError: Invalid container data
        """
        # Validate ID
        self._validate_container_id(container_data.id)
        
        # Validate weight
        if container_data.weight <= 0:
            raise ContainerValidationError(f"Weight must be positive: {container_data.weight}")
        
        if not validate_weight_range(container_data.weight, container_data.unit):
            raise ContainerValidationError(
                f"Weight {container_data.weight} {container_data.unit} is out of valid range"
            )
        
        # Validate unit
        if container_data.unit not in ["kg", "lbs"]:
            raise ContainerValidationError(f"Invalid unit: {container_data.unit}")