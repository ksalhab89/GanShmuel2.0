"""Repository patterns for database operations."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import ContainerRegistered, Transaction
from .schemas import ContainerWeightInfo, SessionPair
import json


# ============================================================================
# Base Repository
# ============================================================================

class BaseRepository:
    """Base repository with common database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()
    
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.session.rollback()
    
    async def refresh(self, instance) -> None:
        """Refresh an instance from the database."""
        await self.session.refresh(instance)


# ============================================================================
# Container Repository
# ============================================================================

class ContainerRepository(BaseRepository):
    """Repository for container operations."""
    
    async def get_by_id(self, container_id: str) -> Optional[ContainerRegistered]:
        """Get container by ID."""
        result = await self.session.execute(
            select(ContainerRegistered).where(ContainerRegistered.container_id == container_id)
        )
        return result.scalar_one_or_none()
    
    async def get_multiple_by_ids(self, container_ids: List[str]) -> Dict[str, ContainerRegistered]:
        """Get multiple containers by IDs."""
        if not container_ids:
            return {}
        
        result = await self.session.execute(
            select(ContainerRegistered).where(ContainerRegistered.container_id.in_(container_ids))
        )
        containers = result.scalars().all()
        return {container.container_id: container for container in containers}
    
    async def create(self, container_id: str, weight: Optional[int], unit: str = "kg") -> ContainerRegistered:
        """Create a new container registration."""
        container = ContainerRegistered(
            container_id=container_id,
            weight=weight,
            unit=unit
        )
        self.session.add(container)
        await self.session.flush()
        return container
    
    async def update_weight(self, container_id: str, weight: int, unit: str = "kg") -> Optional[ContainerRegistered]:
        """Update container weight."""
        container = await self.get_by_id(container_id)
        if container:
            container.weight = weight
            container.unit = unit
            container.updated_at = datetime.now()
            await self.session.flush()
        return container
    
    async def create_or_update(self, container_id: str, weight: int, unit: str = "kg") -> ContainerRegistered:
        """Create new container or update existing one."""
        existing = await self.get_by_id(container_id)
        if existing:
            existing.weight = weight
            existing.unit = unit
            existing.updated_at = datetime.now()
            return existing
        else:
            return await self.create(container_id, weight, unit)
    
    async def get_unknown_containers(self, 
                                   from_time: Optional[datetime] = None,
                                   to_time: Optional[datetime] = None) -> List[str]:
        """Get containers with unknown weights used in transactions."""
        # Base query for transactions in time range
        query = select(Transaction.containers).distinct()
        
        if from_time:
            query = query.where(Transaction.datetime >= from_time)
        if to_time:
            query = query.where(Transaction.datetime <= to_time)
        
        result = await self.session.execute(query)
        container_json_strings = result.scalars().all()
        
        # Parse all container IDs from transactions
        all_container_ids = set()
        for json_str in container_json_strings:
            try:
                container_ids = json.loads(json_str)
            except (json.JSONDecodeError, TypeError):
                container_ids = []
            all_container_ids.update(container_ids)
        
        if not all_container_ids:
            return []
        
        # Get registered containers
        registered_result = await self.session.execute(
            select(ContainerRegistered.container_id)
            .where(
                and_(
                    ContainerRegistered.container_id.in_(all_container_ids),
                    ContainerRegistered.weight.is_not(None)
                )
            )
        )
        known_container_ids = set(registered_result.scalars().all())
        
        # Return unknown containers
        unknown_containers = all_container_ids - known_container_ids
        return sorted(list(unknown_containers))
    
    async def get_all_with_weights(self) -> List[ContainerRegistered]:
        """Get all containers that have known weights."""
        result = await self.session.execute(
            select(ContainerRegistered)
            .where(ContainerRegistered.weight.is_not(None))
            .order_by(ContainerRegistered.container_id)
        )
        return list(result.scalars().all())
    
    async def get_container_weight_info(self, container_ids: List[str]) -> List[ContainerWeightInfo]:
        """Get weight information for containers."""
        if not container_ids:
            return []
        
        containers_dict = await self.get_multiple_by_ids(container_ids)
        
        weight_info = []
        for container_id in container_ids:
            if container_id in containers_dict:
                container = containers_dict[container_id]
                weight_info.append(ContainerWeightInfo(
                    container_id=container_id,
                    weight=container.weight,
                    unit=container.unit,
                    is_known=container.weight is not None
                ))
            else:
                weight_info.append(ContainerWeightInfo(
                    container_id=container_id,
                    weight=None,
                    unit="kg",
                    is_known=False
                ))
        
        return weight_info


# ============================================================================
# Transaction Repository
# ============================================================================

class TransactionRepository(BaseRepository):
    """Repository for transaction operations."""
    
    async def create(self,
                    session_id: str,
                    direction: str,
                    truck: Optional[str],
                    containers: List[str],
                    bruto: int,
                    produce: Optional[str] = None) -> Transaction:
        """Create a new transaction."""
        transaction = Transaction(
            session_id=session_id,
            direction=direction,
            truck=truck,
            containers=json.dumps(containers),
            bruto=bruto,
            produce=produce
        )
        self.session.add(transaction)
        await self.session.flush()
        return transaction
    
    async def get_by_session_id(self, session_id: str) -> List[Transaction]:
        """Get all transactions for a session."""
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.session_id == session_id)
            .order_by(Transaction.datetime)
        )
        return list(result.scalars().all())
    
    async def get_by_session_and_direction(self, session_id: str, direction: str) -> Optional[Transaction]:
        """Get transaction by session ID and direction."""
        result = await self.session.execute(
            select(Transaction)
            .where(
                and_(
                    Transaction.session_id == session_id,
                    Transaction.direction == direction
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_out_transaction(self,
                                   transaction: Transaction,
                                   truck_tara: int,
                                   neto: int) -> Transaction:
        """Update OUT transaction with calculated values."""
        transaction.truck_tara = truck_tara
        transaction.neto = neto
        await self.session.flush()
        return transaction
    
    async def get_transactions_in_range(self,
                                      from_time: Optional[datetime] = None,
                                      to_time: Optional[datetime] = None,
                                      directions: Optional[List[str]] = None,
                                      limit: Optional[int] = None) -> List[Transaction]:
        """Get transactions within time range and direction filter."""
        query = select(Transaction)
        
        # Apply time filters
        if from_time:
            query = query.where(Transaction.datetime >= from_time)
        if to_time:
            query = query.where(Transaction.datetime <= to_time)
        
        # Apply direction filter
        if directions:
            query = query.where(Transaction.direction.in_(directions))
        
        # Order by datetime descending (most recent first)
        query = query.order_by(desc(Transaction.datetime))
        
        # Apply limit
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_transactions_by_truck(self,
                                      truck: str,
                                      from_time: Optional[datetime] = None,
                                      to_time: Optional[datetime] = None) -> List[Transaction]:
        """Get transactions for a specific truck."""
        query = select(Transaction).where(Transaction.truck == truck)
        
        if from_time:
            query = query.where(Transaction.datetime >= from_time)
        if to_time:
            query = query.where(Transaction.datetime <= to_time)
        
        query = query.order_by(desc(Transaction.datetime))
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_sessions_with_container(self,
                                        container_id: str,
                                        from_time: Optional[datetime] = None,
                                        to_time: Optional[datetime] = None) -> List[str]:
        """Get session IDs that used a specific container."""
        query = select(Transaction.session_id).distinct()
        
        # Use JSON search for container ID
        query = query.where(Transaction.containers.like(f'%"{container_id}"%'))
        
        if from_time:
            query = query.where(Transaction.datetime >= from_time)
        if to_time:
            query = query.where(Transaction.datetime <= to_time)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def find_matching_in_transaction(self, 
                                         truck: Optional[str],
                                         containers: List[str]) -> Optional[Transaction]:
        """Find matching IN transaction for OUT transaction."""
        # Look for IN transactions with same truck and containers
        query = select(Transaction).where(
            and_(
                Transaction.direction == "in",
                Transaction.truck_tara.is_(None),  # Not yet processed as OUT
                Transaction.neto.is_(None)  # Not yet processed as OUT
            )
        )
        
        if truck and truck != "na":
            query = query.where(Transaction.truck == truck)
        
        # Get candidates and check container match
        result = await self.session.execute(query.order_by(desc(Transaction.datetime)))
        candidates = result.scalars().all()
        
        containers_set = set(containers)
        for candidate in candidates:
            candidate_containers = set(candidate.container_list)
            if candidate_containers == containers_set:
                return candidate
        
        return None
    
    async def get_session_statistics(self,
                                   from_time: Optional[datetime] = None,
                                   to_time: Optional[datetime] = None) -> Dict[str, int]:
        """Get transaction statistics."""
        query = select(
            Transaction.direction,
            func.count(Transaction.id).label('count')
        )
        
        if from_time:
            query = query.where(Transaction.datetime >= from_time)
        if to_time:
            query = query.where(Transaction.datetime <= to_time)
        
        query = query.group_by(Transaction.direction)
        
        result = await self.session.execute(query)
        stats = dict(result.all())
        
        # Ensure all directions are present
        for direction in ['in', 'out', 'none']:
            if direction not in stats:
                stats[direction] = 0
        
        stats['total'] = sum(stats.values())
        return stats


# ============================================================================
# Session Management Repository
# ============================================================================

class SessionRepository(BaseRepository):
    """Repository for session-level operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.container_repo = ContainerRepository(session)
        self.transaction_repo = TransactionRepository(session)
    
    def generate_session_id(self) -> str:
        """Generate a new session ID."""
        return str(uuid4())
    
    async def create_weighing_session(self,
                                    direction: str,
                                    truck: Optional[str],
                                    containers: List[str],
                                    weight: int,
                                    unit: str,
                                    produce: Optional[str] = None,
                                    force: bool = False) -> Tuple[Transaction, Optional[str]]:
        """Create a new weighing session with business logic."""
        # Normalize weight to kg
        bruto_kg = weight
        if unit == "lbs":
            bruto_kg = int(weight * 0.453592)
        
        # Handle different directions
        if direction == "in":
            return await self._create_in_transaction(truck, containers, bruto_kg, produce, force)
        elif direction == "out":
            return await self._create_out_transaction(truck, containers, bruto_kg, produce)
        else:  # direction == "none"
            return await self._create_none_transaction(truck, containers, bruto_kg, produce)
    
    async def _create_in_transaction(self,
                                   truck: Optional[str],
                                   containers: List[str],
                                   bruto: int,
                                   produce: Optional[str],
                                   force: bool) -> Tuple[Transaction, Optional[str]]:
        """Create IN transaction."""
        session_id = self.generate_session_id()
        
        # Check for existing IN transaction if not forcing
        if not force:
            existing = await self.transaction_repo.find_matching_in_transaction(truck, containers)
            if existing:
                return existing, "Existing IN transaction found (use force=true to override)"
        
        transaction = await self.transaction_repo.create(
            session_id=session_id,
            direction="in",
            truck=truck,
            containers=containers,
            bruto=bruto,
            produce=produce
        )
        
        return transaction, None
    
    async def _create_out_transaction(self,
                                    truck: Optional[str],
                                    containers: List[str],
                                    bruto: int,
                                    produce: Optional[str]) -> Tuple[Transaction, Optional[str]]:
        """Create OUT transaction with weight calculations."""
        # Find matching IN transaction
        in_transaction = await self.transaction_repo.find_matching_in_transaction(truck, containers)
        if not in_transaction:
            return None, "No matching IN transaction found"
        
        # Get container weights
        container_weights_info = await self.container_repo.get_container_weight_info(containers)
        unknown_containers = [info.container_id for info in container_weights_info if not info.is_known]
        
        if unknown_containers:
            return None, f"Unknown container weights: {', '.join(unknown_containers)}"
        
        # Calculate weights
        container_weights_kg = [info.weight_in_kg for info in container_weights_info if info.weight_in_kg is not None]
        total_container_tara = sum(container_weights_kg)
        
        # Calculate truck tare and net weight
        truck_tara = in_transaction.bruto - bruto - total_container_tara
        neto = max(0, in_transaction.bruto - truck_tara - total_container_tara)
        
        # Update IN transaction with calculated values
        await self.transaction_repo.update_out_transaction(in_transaction, truck_tara, neto)
        
        # Create OUT transaction
        out_transaction = await self.transaction_repo.create(
            session_id=in_transaction.session_id,
            direction="out",
            truck=truck,
            containers=containers,
            bruto=bruto,
            produce=produce
        )
        
        # Update OUT transaction with calculated values
        await self.transaction_repo.update_out_transaction(out_transaction, truck_tara, neto)
        
        return out_transaction, None
    
    async def _create_none_transaction(self,
                                     truck: Optional[str],
                                     containers: List[str],
                                     bruto: int,
                                     produce: Optional[str]) -> Tuple[Transaction, Optional[str]]:
        """Create NONE transaction (simple weighing)."""
        session_id = self.generate_session_id()
        
        transaction = await self.transaction_repo.create(
            session_id=session_id,
            direction="none",
            truck=truck,
            containers=containers,
            bruto=bruto,
            produce=produce
        )
        
        return transaction, None
    
    async def get_session_details(self, session_id: str) -> Optional[SessionPair]:
        """Get complete session details with IN/OUT transactions."""
        transactions = await self.transaction_repo.get_by_session_id(session_id)
        
        if not transactions:
            return None
        
        session_pair = SessionPair(session_id=session_id)
        
        for transaction in transactions:
            if transaction.direction == "in":
                session_pair.in_transaction = transaction
            elif transaction.direction == "out":
                session_pair.out_transaction = transaction
        
        session_pair.is_complete = session_pair.has_both_transactions
        
        return session_pair