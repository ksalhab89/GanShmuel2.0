"""Data query service for transaction and item information retrieval."""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import Transaction
from ..models.repositories import ContainerRepository, TransactionRepository
from ..models.schemas import ItemResponse, TransactionResponse, WeightQueryParams, ItemQueryParams
from ..utils.datetime_utils import parse_datetime_string
from ..utils.exceptions import InvalidDateRangeError
from .container_service import ContainerService
from .session_service import SessionService


class QueryService:
    """Data query service for retrieving transaction and item information."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.transaction_repo = TransactionRepository(session)
        self.container_repo = ContainerRepository(session)
        self.container_service = ContainerService(session)
        self.session_service = SessionService(session)
    
    async def query_transactions(self, params: WeightQueryParams) -> List[TransactionResponse]:
        """
        Main transaction query method with filtering.
        
        Args:
            params: Query parameters with time range and direction filters
            
        Returns:
            List of TransactionResponse objects
        """
        # Parse time range
        from_time = None
        to_time = None

        if params.from_time:
            from_time = parse_datetime_string(params.from_time)

        if params.to_time:
            to_time = parse_datetime_string(params.to_time)

        # Validate date range
        if from_time and to_time and from_time > to_time:
            raise InvalidDateRangeError("From date cannot be after To date")

        # Parse direction filter
        directions = [d.strip() for d in params.filter.split(',') if d.strip()]
        
        # Query transactions
        transactions = await self.transaction_repo.get_transactions_in_range(
            from_time=from_time,
            to_time=to_time,
            directions=directions
        )
        
        # Convert to response format
        return [self._transaction_to_response(t) for t in transactions]
    
    async def query_by_time_range(self,
                                from_time: datetime,
                                to_time: datetime,
                                directions: Optional[List[str]] = None,
                                limit: Optional[int] = None) -> List[TransactionResponse]:
        """
        Query transactions within specific time range.
        
        Args:
            from_time: Start time
            to_time: End time
            directions: Direction filter
            limit: Maximum results
            
        Returns:
            List of TransactionResponse objects
        """
        transactions = await self.transaction_repo.get_transactions_in_range(
            from_time=from_time,
            to_time=to_time,
            directions=directions,
            limit=limit
        )
        
        return [self._transaction_to_response(t) for t in transactions]
    
    async def query_by_direction(self,
                               direction: str,
                               from_time: Optional[datetime] = None,
                               to_time: Optional[datetime] = None,
                               limit: Optional[int] = None) -> List[TransactionResponse]:
        """
        Query transactions by direction.
        
        Args:
            direction: Transaction direction ('in', 'out', 'none')
            from_time: Start time filter
            to_time: End time filter
            limit: Maximum results
            
        Returns:
            List of TransactionResponse objects
        """
        return await self.query_by_time_range(
            from_time=from_time or datetime.min,
            to_time=to_time or datetime.max,
            directions=[direction],
            limit=limit
        )
    
    async def query_by_truck(self,
                           truck: str,
                           from_time: Optional[datetime] = None,
                           to_time: Optional[datetime] = None) -> List[TransactionResponse]:
        """
        Query transactions for specific truck.
        
        Args:
            truck: Truck license plate
            from_time: Start time filter
            to_time: End time filter
            
        Returns:
            List of TransactionResponse objects
        """
        transactions = await self.transaction_repo.get_transactions_by_truck(
            truck=truck,
            from_time=from_time,
            to_time=to_time
        )
        
        return [self._transaction_to_response(t) for t in transactions]
    
    async def get_truck_info(self, truck_id: str, params: Optional[ItemQueryParams] = None) -> ItemResponse:
        """
        Get truck details and session history.
        
        Args:
            truck_id: Truck license plate
            params: Query parameters for time filtering
            
        Returns:
            ItemResponse with truck information
        """
        # Parse time filters if provided
        from_time = None
        to_time = None
        
        if params:
            if params.from_time:
                from_time = parse_datetime_string(params.from_time)
            if params.to_time:
                to_time = parse_datetime_string(params.to_time)
        
        # Get transactions for truck
        transactions = await self.transaction_repo.get_transactions_by_truck(
            truck=truck_id,
            from_time=from_time,
            to_time=to_time
        )
        
        # Get unique session IDs
        session_ids = list(set(t.session_id for t in transactions))
        
        # Calculate average truck tare if available
        truck_tara_weights = [t.truck_tara for t in transactions if t.truck_tara is not None]
        avg_tara = sum(truck_tara_weights) // len(truck_tara_weights) if truck_tara_weights else "na"
        
        return ItemResponse(
            id=truck_id,
            item_type="truck",
            tara=avg_tara,
            sessions=session_ids
        )
    
    async def get_container_info(self, container_id: str, params: Optional[ItemQueryParams] = None) -> ItemResponse:
        """
        Get container weight and usage information.
        
        Args:
            container_id: Container identifier
            params: Query parameters for time filtering
            
        Returns:
            ItemResponse with container information
        """
        # Get container weight
        container_info = await self.container_service.get_container_weight(container_id)
        
        # Parse time filters if provided
        from_time = None
        to_time = None
        
        if params:
            if params.from_time:
                from_time = parse_datetime_string(params.from_time)
            if params.to_time:
                to_time = parse_datetime_string(params.to_time)
        
        # Get sessions using this container
        session_ids = await self.transaction_repo.get_sessions_with_container(
            container_id=container_id,
            from_time=from_time,
            to_time=to_time
        )
        
        # Format tare weight
        tara = container_info.weight if container_info and container_info.is_known else "na"
        
        return ItemResponse(
            id=container_id,
            item_type="container",
            tara=tara,
            sessions=session_ids
        )
    
    async def get_item_info(self, 
                           item_id: str,
                           from_datetime: Optional[str] = None,
                           to_datetime: Optional[str] = None) -> Optional[ItemResponse]:
        """
        Get comprehensive information about a truck or container.
        
        Args:
            item_id: Truck license or container ID
            from_datetime: Start datetime string (yyyymmddhhmmss)
            to_datetime: End datetime string (yyyymmddhhmmss)
            
        Returns:
            ItemResponse with item details and session history
        """
        # Parse datetime parameters
        from_time = None
        to_time = None
        
        if from_datetime:
            from_time = parse_datetime_string(from_datetime)
        if to_datetime:
            to_time = parse_datetime_string(to_datetime)
        
        # Detect item type
        item_type = await self._detect_item_type(item_id)
        
        if item_type == "unknown":
            return None
        
        # Get sessions for this item
        sessions = await self.get_item_sessions(
            item_id=item_id,
            item_type=item_type,
            from_time=from_time,
            to_time=to_time
        )
        
        # Get last known tare weight for containers
        last_tare_weight = "na"
        if item_type == "container":
            try:
                container = await self.container_repo.get_by_id(item_id)
                if container:
                    last_tare_weight = str(container.weight)
            except Exception:
                pass
        
        return ItemResponse(
            id=item_id,
            item_type=item_type,
            tara=last_tare_weight,
            sessions=sessions
        )
    
    async def get_item_sessions(self, 
                              item_id: str,
                              item_type: str = "auto",
                              from_time: Optional[datetime] = None,
                              to_time: Optional[datetime] = None) -> List[str]:
        """
        Get session IDs associated with an item (truck or container).
        
        Args:
            item_id: Item identifier
            item_type: Type of item ('truck', 'container', 'auto')
            from_time: Start time filter
            to_time: End time filter
            
        Returns:
            List of session IDs
        """
        if item_type == "auto":
            # Try to detect item type based on usage patterns
            item_type = await self._detect_item_type(item_id)
        
        if item_type == "container":
            return await self.transaction_repo.get_sessions_with_container(
                container_id=item_id,
                from_time=from_time,
                to_time=to_time
            )
        elif item_type == "truck":
            transactions = await self.transaction_repo.get_transactions_by_truck(
                truck=item_id,
                from_time=from_time,
                to_time=to_time
            )
            return list(set(t.session_id for t in transactions))
        else:
            return []
    
    async def calculate_item_statistics(self,
                                      item_id: str,
                                      item_type: str = "auto",
                                      from_time: Optional[datetime] = None,
                                      to_time: Optional[datetime] = None) -> Dict[str, any]:
        """
        Calculate usage analytics for an item.
        
        Args:
            item_id: Item identifier
            item_type: Type of item ('truck', 'container', 'auto')
            from_time: Start time filter
            to_time: End time filter
            
        Returns:
            Dictionary with usage statistics
        """
        if item_type == "auto":
            item_type = await self._detect_item_type(item_id)
        
        if item_type == "container":
            return await self._calculate_container_statistics(item_id, from_time, to_time)
        elif item_type == "truck":
            return await self._calculate_truck_statistics(item_id, from_time, to_time)
        else:
            return {
                "item_id": item_id,
                "item_type": "unknown",
                "total_sessions": 0,
                "total_transactions": 0
            }
    
    async def get_query_performance_info(self,
                                       from_time: Optional[datetime] = None,
                                       to_time: Optional[datetime] = None) -> Dict[str, any]:
        """
        Get query performance information and database statistics.
        
        Args:
            from_time: Start time filter
            to_time: End time filter
            
        Returns:
            Dictionary with performance metrics
        """
        # Get transaction statistics
        stats = await self.transaction_repo.get_session_statistics(from_time, to_time)
        
        # Get container statistics
        all_containers = await self.container_repo.get_all_with_weights()
        unknown_containers = await self.container_repo.get_unknown_containers(from_time, to_time)
        
        return {
            "time_range": {
                "from_time": from_time.isoformat() if from_time else None,
                "to_time": to_time.isoformat() if to_time else None
            },
            "transaction_stats": stats,
            "container_stats": {
                "registered_containers": len(all_containers),
                "unknown_containers": len(unknown_containers),
                "total_containers_used": len(all_containers) + len(unknown_containers)
            },
            "database_info": {
                "indexes_available": [
                    "transactions.session_id",
                    "transactions.direction", 
                    "transactions.truck",
                    "transactions.datetime",
                    "containers_registered.container_id"
                ]
            }
        }
    
    async def search_transactions(self,
                                search_term: str,
                                search_fields: List[str] = None,
                                from_time: Optional[datetime] = None,
                                to_time: Optional[datetime] = None,
                                limit: int = 100) -> List[TransactionResponse]:
        """
        Search transactions by various criteria.
        
        Args:
            search_term: Term to search for
            search_fields: Fields to search in ('truck', 'produce', 'containers')
            from_time: Start time filter
            to_time: End time filter
            limit: Maximum results
            
        Returns:
            List of matching TransactionResponse objects
        """
        if not search_fields:
            search_fields = ['truck', 'produce', 'containers']
        
        # Get all transactions in time range
        transactions = await self.transaction_repo.get_transactions_in_range(
            from_time=from_time,
            to_time=to_time,
            limit=limit * 2  # Get extra to allow for filtering
        )
        
        # Filter by search term
        matching_transactions = []
        
        for transaction in transactions:
            if len(matching_transactions) >= limit:
                break
                
            # Check each search field
            if 'truck' in search_fields and transaction.truck:
                if search_term.lower() in transaction.truck.lower():
                    matching_transactions.append(transaction)
                    continue
            
            if 'produce' in search_fields and transaction.produce:
                if search_term.lower() in transaction.produce.lower():
                    matching_transactions.append(transaction)
                    continue
            
            if 'containers' in search_fields:
                container_list = transaction.container_list
                if any(search_term.lower() in container.lower() for container in container_list):
                    matching_transactions.append(transaction)
                    continue
        
        return [self._transaction_to_response(t) for t in matching_transactions]
    
    def _transaction_to_response(self, transaction: Transaction) -> TransactionResponse:
        """
        Convert Transaction model to TransactionResponse.
        
        Args:
            transaction: Transaction database model
            
        Returns:
            TransactionResponse object
        """
        return TransactionResponse(
            id=transaction.session_id,
            direction=transaction.direction,
            truck=transaction.truck,
            bruto=transaction.bruto,
            gross_weight=transaction.bruto,
            neto=transaction.neto if transaction.neto is not None else "na",
            produce=transaction.get_display_produce(),
            containers=transaction.container_list
        )
    
    async def _detect_item_type(self, item_id: str) -> str:
        """
        Detect if item is a truck or container based on usage patterns.
        
        Args:
            item_id: Item identifier
            
        Returns:
            Detected item type ('truck', 'container', 'unknown')
        """
        # Check if it's a registered container
        container_info = await self.container_service.get_container_weight(item_id)
        if container_info and container_info.is_known:
            return "container"
        
        # Check transactions to see usage pattern
        truck_transactions = await self.transaction_repo.get_transactions_by_truck(item_id)
        container_sessions = await self.transaction_repo.get_sessions_with_container(item_id)
        
        if truck_transactions and not container_sessions:
            return "truck"
        elif container_sessions and not truck_transactions:
            return "container"
        elif container_sessions:
            # If used as container more often, classify as container
            return "container"
        elif truck_transactions:
            return "truck"
        else:
            return "unknown"
    
    async def _calculate_container_statistics(self,
                                            container_id: str,
                                            from_time: Optional[datetime],
                                            to_time: Optional[datetime]) -> Dict[str, any]:
        """Calculate statistics for a container."""
        # Get container info
        container_info = await self.container_service.get_container_weight(container_id)
        
        # Get usage sessions
        session_ids = await self.transaction_repo.get_sessions_with_container(
            container_id, from_time, to_time
        )
        
        # Get all transactions using this container
        all_transactions = await self.transaction_repo.get_transactions_in_range(
            from_time=from_time,
            to_time=to_time
        )
        
        container_transactions = [
            t for t in all_transactions
            if container_id in t.container_list
        ]
        
        return {
            "item_id": container_id,
            "item_type": "container",
            "is_registered": container_info.is_known if container_info else False,
            "weight": container_info.weight if container_info else None,
            "total_sessions": len(session_ids),
            "total_transactions": len(container_transactions),
            "direction_breakdown": {
                "in": len([t for t in container_transactions if t.direction == "in"]),
                "out": len([t for t in container_transactions if t.direction == "out"]),
                "none": len([t for t in container_transactions if t.direction == "none"])
            }
        }
    
    async def _calculate_truck_statistics(self,
                                        truck_id: str,
                                        from_time: Optional[datetime],
                                        to_time: Optional[datetime]) -> Dict[str, any]:
        """Calculate statistics for a truck."""
        transactions = await self.transaction_repo.get_transactions_by_truck(
            truck_id, from_time, to_time
        )
        
        session_ids = list(set(t.session_id for t in transactions))
        
        # Calculate truck tare statistics
        truck_tara_weights = [t.truck_tara for t in transactions if t.truck_tara is not None]
        avg_tara = sum(truck_tara_weights) // len(truck_tara_weights) if truck_tara_weights else None
        
        return {
            "item_id": truck_id,
            "item_type": "truck",
            "total_sessions": len(session_ids),
            "total_transactions": len(transactions),
            "average_tara": avg_tara,
            "direction_breakdown": {
                "in": len([t for t in transactions if t.direction == "in"]),
                "out": len([t for t in transactions if t.direction == "out"]),
                "none": len([t for t in transactions if t.direction == "none"])
            }
        }