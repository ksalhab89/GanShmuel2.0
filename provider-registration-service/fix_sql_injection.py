"""Script to fix SQL injection vulnerability in candidate_service.py"""
import re

with open('src/services/candidate_service.py', 'r') as f:
    content = f.read()

# Define the new secure implementation
new_method = '''    async def list_candidates(
        self,
        status: Optional[str],
        product: Optional[str],
        limit: int,
        offset: int
    ) -> Tuple[List[CandidateResponse], int]:
        """
        List candidates with SAFE parameterized queries

        SECURITY FIX: Uses NULL-safe conditions instead of dynamic WHERE clause
        No string interpolation - all values passed as parameters

        Args:
            status: Optional status filter (pending, approved, rejected)
            product: Optional product filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (list of candidates, total count)
        """

        # SAFE: Use NULL-safe conditions with proper parameter binding
        # All filtering logic is INSIDE the SQL query, not built dynamically
        query = text("""
            SELECT id, status, company_name, contact_email, phone, products,
                   truck_count, capacity_tons_per_day, location, created_at,
                   provider_id, version
            FROM candidates
            WHERE (:status IS NULL OR status = :status)
              AND (:product IS NULL OR products @> CAST(:product AS jsonb))
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        # All parameters passed separately - SAFE
        params = {
            "status": status,
            "product": json.dumps([product]) if product else None,
            "limit": limit,
            "offset": offset
        }

        result = await self.db.execute(query, params)
        rows = result.fetchall()

        # SAFE: Count query with same NULL-safe pattern
        count_query = text("""
            SELECT COUNT(*) FROM candidates
            WHERE (:status IS NULL OR status = :status)
              AND (:product IS NULL OR products @> CAST(:product AS jsonb))
        """)

        count_params = {
            "status": status,
            "product": json.dumps([product]) if product else None
        }

        total = (await self.db.execute(count_query, count_params)).scalar()

        # Build responses using DRY helper
        candidates = [self._build_response(row) for row in rows]

        return candidates, total'''

# Pattern to match the vulnerable method
pattern = r'    async def list_candidates\(.*?\n        return candidates, total'

# Replace with secure implementation
content = re.sub(pattern, new_method, content, flags=re.DOTALL)

with open('src/services/candidate_service.py', 'w') as f:
    f.write(content)

print('[OK] Fixed SQL injection vulnerability in candidate_service.py')
print('[OK] Replaced dynamic WHERE clause with NULL-safe parameterized queries')
