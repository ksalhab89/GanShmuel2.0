"""Session lifecycle management service."""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import Transaction
from ..models.repositories import SessionRepository, TransactionRepository
from ..models.schemas import SessionPair, SessionResponse


class SessionNotFoundError(Exception):
    """Exception raised when session is not found."""
    pass


class SessionStateError(Exception):
    """Exception raised for invalid session state operations."""
    pass


class SessionService:
    """Session lifecycle management service."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_repo = SessionRepository(session)
        self.transaction_repo = TransactionRepository(session)
    
    async def create_session(self, 
                           direction: str,
                           truck: Optional[str],
                           containers: List[str],
                           bruto: int,
                           produce: Optional[str] = None) -> Tuple[str, Transaction]:
        """
        Create a new session with initial transaction.
        
        Args:
            direction: Transaction direction
            truck: Truck license
            containers: Container IDs
            bruto: Gross weight
            produce: Produce type
            
        Returns:
            Tuple of (session_id, transaction)
        """
        session_id = self._generate_session_id()
        
        transaction = await self.transaction_repo.create(
            session_id=session_id,
            direction=direction,
            truck=truck,
            containers=containers,
            bruto=bruto,
            produce=produce
        )
        
        await self.session.commit()
        return session_id, transaction
    
    async def complete_session(self,
                             session_id: str,
                             direction: str,
                             truck: Optional[str],
                             containers: List[str],
                             bruto: int,
                             truck_tara: int,
                             neto: int,
                             produce: Optional[str] = None) -> Transaction:
        """
        Complete a session with final transaction (typically OUT).
        
        Args:
            session_id: Session identifier
            direction: Transaction direction
            truck: Truck license
            containers: Container IDs
            bruto: Gross weight
            truck_tara: Truck tare weight
            neto: Net weight
            produce: Produce type
            
        Returns:
            Completed transaction
            
        Raises:
            SessionNotFoundError: Session not found
        """
        # Verify session exists
        existing_transactions = await self.transaction_repo.get_by_session_id(session_id)
        if not existing_transactions:
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        # Create completion transaction
        transaction = await self.transaction_repo.create(
            session_id=session_id,
            direction=direction,
            truck=truck,
            containers=containers,
            bruto=bruto,
            produce=produce
        )
        
        # Update with calculated values
        await self.transaction_repo.update_out_transaction(transaction, truck_tara, neto)
        
        # Also update the IN transaction if this is an OUT
        if direction == "out":
            in_transaction = await self.transaction_repo.get_by_session_and_direction(session_id, "in")
            if in_transaction:
                await self.transaction_repo.update_out_transaction(in_transaction, truck_tara, neto)
        
        await self.session.commit()
        return transaction
    
    async def get_session_details(self, session_id: str) -> Optional[SessionPair]:
        """
        Get complete session details with all transactions.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionPair or None if not found
        """
        return await self.session_repo.get_session_details(session_id)
    
    async def get_session_response(self, session_id: str) -> Optional[SessionResponse]:
        """
        Get session response formatted for API.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionResponse or None if not found
        """
        session_pair = await self.get_session_details(session_id)
        if not session_pair:
            return None
        
        # Use the most recent transaction for response
        transaction = session_pair.out_transaction or session_pair.in_transaction
        if not transaction:
            return None
        
        return SessionResponse(
            id=session_id,
            truck=transaction.get_display_truck(),
            bruto=transaction.bruto,
            truck_tara=transaction.truck_tara,
            neto=transaction.neto if transaction.neto is not None else "na"
        )
    
    async def find_active_sessions(self, 
                                 truck: Optional[str] = None,
                                 from_time: Optional[datetime] = None,
                                 to_time: Optional[datetime] = None) -> List[SessionPair]:
        """
        Find active sessions (IN without matching OUT).
        
        Args:
            truck: Filter by truck license
            from_time: Start time filter
            to_time: End time filter
            
        Returns:
            List of active SessionPair objects
        """
        # Get all IN transactions in time range
        directions = ["in"]
        transactions = await self.transaction_repo.get_transactions_in_range(
            from_time=from_time,
            to_time=to_time,
            directions=directions
        )
        
        # Filter by truck if specified
        if truck:
            transactions = [t for t in transactions if t.truck == truck]
        
        # Check which sessions are incomplete
        active_sessions = []
        
        for transaction in transactions:
            # Check if there's a matching OUT transaction
            out_transaction = await self.transaction_repo.get_by_session_and_direction(
                transaction.session_id, "out"
            )
            
            if not out_transaction:
                # This is an active session
                session_pair = SessionPair(
                    session_id=transaction.session_id,
                    in_transaction=transaction,
                    out_transaction=None,
                    is_complete=False
                )
                active_sessions.append(session_pair)
        
        return active_sessions
    
    async def get_sessions_by_truck(self,
                                  truck: str,
                                  from_time: Optional[datetime] = None,
                                  to_time: Optional[datetime] = None) -> List[SessionPair]:
        """
        Get all sessions for a specific truck.
        
        Args:
            truck: Truck license
            from_time: Start time filter
            to_time: End time filter
            
        Returns:
            List of SessionPair objects
        """
        transactions = await self.transaction_repo.get_transactions_by_truck(
            truck, from_time, to_time
        )
        
        # Group transactions by session
        sessions_dict = {}
        for transaction in transactions:
            session_id = transaction.session_id
            if session_id not in sessions_dict:
                sessions_dict[session_id] = SessionPair(
                    session_id=session_id,
                    in_transaction=None,
                    out_transaction=None,
                    is_complete=False
                )
            
            if transaction.direction == "in":
                sessions_dict[session_id].in_transaction = transaction
            elif transaction.direction == "out":
                sessions_dict[session_id].out_transaction = transaction
        
        # Update completion status
        for session_pair in sessions_dict.values():
            session_pair.is_complete = session_pair.has_both_transactions
        
        return list(sessions_dict.values())
    
    async def get_sessions_by_time_range(self,
                                       from_time: datetime,
                                       to_time: datetime,
                                       directions: Optional[List[str]] = None) -> List[SessionPair]:
        """
        Get sessions within time range.
        
        Args:
            from_time: Start time
            to_time: End time
            directions: Filter by directions
            
        Returns:
            List of SessionPair objects
        """
        transactions = await self.transaction_repo.get_transactions_in_range(
            from_time=from_time,
            to_time=to_time,
            directions=directions
        )
        
        # Group by session
        sessions_dict = {}
        for transaction in transactions:
            session_id = transaction.session_id
            if session_id not in sessions_dict:
                sessions_dict[session_id] = SessionPair(
                    session_id=session_id,
                    in_transaction=None,
                    out_transaction=None,
                    is_complete=False
                )
            
            if transaction.direction == "in":
                sessions_dict[session_id].in_transaction = transaction
            elif transaction.direction == "out":
                sessions_dict[session_id].out_transaction = transaction
        
        # Update completion status
        for session_pair in sessions_dict.values():
            session_pair.is_complete = session_pair.has_both_transactions
        
        return list(sessions_dict.values())
    
    async def get_sessions_by_produce_type(self,
                                         produce: str,
                                         from_time: Optional[datetime] = None,
                                         to_time: Optional[datetime] = None) -> List[SessionPair]:
        """
        Get sessions by produce type.
        
        Args:
            produce: Produce type
            from_time: Start time filter
            to_time: End time filter
            
        Returns:
            List of SessionPair objects
        """
        transactions = await self.transaction_repo.get_transactions_in_range(
            from_time=from_time,
            to_time=to_time
        )
        
        # Filter by produce type
        filtered_transactions = [
            t for t in transactions 
            if t.produce == produce or (produce == "na" and t.produce is None)
        ]
        
        # Group by session
        sessions_dict = {}
        for transaction in filtered_transactions:
            session_id = transaction.session_id
            if session_id not in sessions_dict:
                sessions_dict[session_id] = SessionPair(
                    session_id=session_id,
                    in_transaction=None,
                    out_transaction=None,
                    is_complete=False
                )
            
            if transaction.direction == "in":
                sessions_dict[session_id].in_transaction = transaction
            elif transaction.direction == "out":
                sessions_dict[session_id].out_transaction = transaction
        
        # Update completion status
        for session_pair in sessions_dict.values():
            session_pair.is_complete = session_pair.has_both_transactions
        
        return list(sessions_dict.values())
    
    async def filter_sessions_by_completion_status(self,
                                                 sessions: List[SessionPair],
                                                 completed_only: bool = False,
                                                 incomplete_only: bool = False) -> List[SessionPair]:
        """
        Filter sessions by completion status.
        
        Args:
            sessions: List of sessions to filter
            completed_only: Return only completed sessions
            incomplete_only: Return only incomplete sessions
            
        Returns:
            Filtered list of sessions
        """
        if completed_only:
            return [s for s in sessions if s.is_complete]
        elif incomplete_only:
            return [s for s in sessions if not s.is_complete]
        else:
            return sessions
    
    async def calculate_session_metrics(self,
                                      from_time: Optional[datetime] = None,
                                      to_time: Optional[datetime] = None) -> Dict[str, any]:
        """
        Calculate session metrics and statistics.
        
        Args:
            from_time: Start time filter
            to_time: End time filter
            
        Returns:
            Dictionary with session metrics
        """
        # Get transaction statistics
        stats = await self.transaction_repo.get_session_statistics(from_time, to_time)
        
        # Get sessions in time range
        transactions = await self.transaction_repo.get_transactions_in_range(
            from_time=from_time,
            to_time=to_time
        )
        
        # Count unique sessions
        unique_sessions = set(t.session_id for t in transactions)
        
        # Count completed sessions (have both IN and OUT)
        session_transaction_counts = {}
        for transaction in transactions:
            session_id = transaction.session_id
            if session_id not in session_transaction_counts:
                session_transaction_counts[session_id] = set()
            session_transaction_counts[session_id].add(transaction.direction)
        
        completed_sessions = sum(
            1 for directions in session_transaction_counts.values()
            if "in" in directions and "out" in directions
        )
        
        incomplete_sessions = len(unique_sessions) - completed_sessions
        
        return {
            "total_transactions": stats["total"],
            "in_transactions": stats["in"],
            "out_transactions": stats["out"],
            "none_transactions": stats["none"],
            "total_sessions": len(unique_sessions),
            "completed_sessions": completed_sessions,
            "incomplete_sessions": incomplete_sessions,
            "completion_rate": completed_sessions / len(unique_sessions) if unique_sessions else 0
        }
    
    async def cleanup_abandoned_sessions(self,
                                       older_than_hours: int = 24) -> Dict[str, any]:
        """
        Identify and optionally clean up abandoned sessions.
        
        Args:
            older_than_hours: Consider sessions older than this as abandoned
            
        Returns:
            Dictionary with cleanup information
        """
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        
        # Find old IN transactions without matching OUT
        old_in_transactions = await self.transaction_repo.get_transactions_in_range(
            to_time=cutoff_time,
            directions=["in"]
        )
        
        abandoned_sessions = []
        for transaction in old_in_transactions:
            # Check if there's a matching OUT
            out_transaction = await self.transaction_repo.get_by_session_and_direction(
                transaction.session_id, "out"
            )
            if not out_transaction:
                abandoned_sessions.append({
                    "session_id": transaction.session_id,
                    "truck": transaction.get_display_truck(),
                    "containers": transaction.container_list,
                    "created_at": transaction.datetime,
                    "hours_old": (datetime.now() - transaction.datetime).total_seconds() / 3600
                })
        
        return {
            "total_abandoned": len(abandoned_sessions),
            "cutoff_hours": older_than_hours,
            "abandoned_sessions": abandoned_sessions
        }
    
    def _generate_session_id(self) -> str:
        """
        Generate a new session ID.
        
        Returns:
            UUID session identifier
        """
        return str(uuid.uuid4())
    
    async def validate_session_state(self, session_id: str, expected_state: str) -> Tuple[bool, Optional[str]]:
        """
        Validate session is in expected state.
        
        Args:
            session_id: Session identifier
            expected_state: Expected state ('active', 'completed', 'exists')
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        session_pair = await self.get_session_details(session_id)
        
        if not session_pair:
            return False, f"Session {session_id} not found"
        
        if expected_state == "active" and session_pair.is_complete:
            return False, f"Session {session_id} is already completed"
        
        if expected_state == "completed" and not session_pair.is_complete:
            return False, f"Session {session_id} is not completed"
        
        return True, None