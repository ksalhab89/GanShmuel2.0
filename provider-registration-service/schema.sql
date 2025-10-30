-- Provider Candidate Registration Schema
-- PostgreSQL database schema for provider registration service

CREATE TABLE IF NOT EXISTS candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),
    products JSONB,
    truck_count INTEGER CHECK (truck_count > 0),
    capacity_tons_per_day INTEGER CHECK (capacity_tons_per_day > 0),
    location VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    provider_id INTEGER, -- Reference to billing service provider
    version INTEGER DEFAULT 1 NOT NULL, -- Optimistic locking version
    rejection_reason TEXT, -- Optional reason for rejection
    CONSTRAINT status_check CHECK (status IN ('pending', 'approved', 'rejected'))
);

-- Indexes for efficient querying
CREATE INDEX idx_candidates_status ON candidates(status);
CREATE INDEX idx_candidates_created_at ON candidates(created_at DESC);
CREATE INDEX idx_candidates_products ON candidates USING GIN (products);
CREATE INDEX idx_candidates_version ON candidates(id, version); -- For optimistic locking

-- Trigger to update updated_at and version on updates
CREATE OR REPLACE FUNCTION update_candidates_metadata()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_candidates_metadata BEFORE UPDATE ON candidates
FOR EACH ROW EXECUTE FUNCTION update_candidates_metadata();
