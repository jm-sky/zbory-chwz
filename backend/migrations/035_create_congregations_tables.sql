-- Migration: Create congregations tables (addresses, service times, contact persons)
-- This migration creates tables for congregation addresses, service times,
-- and contact persons.

-- Upgrade: Create tables
CREATE TABLE IF NOT EXISTS congregation_addresses (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    street VARCHAR(255),
    city VARCHAR(255) NOT NULL,
    postal_code VARCHAR(20),
    province VARCHAR(100),
    country VARCHAR(100) NOT NULL DEFAULT 'Poland',
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS congregation_service_times (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    day VARCHAR(50) NOT NULL,
    time VARCHAR(10) NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS congregation_contact_persons (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    title VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),
    "order" INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_congregation_addresses_tenant_id ON congregation_addresses(tenant_id);
CREATE INDEX IF NOT EXISTS idx_congregation_service_times_tenant_id ON congregation_service_times(tenant_id);
CREATE INDEX IF NOT EXISTS idx_congregation_contact_persons_tenant_id ON congregation_contact_persons(tenant_id);

-- Downgrade: Drop tables
-- DROP TABLE IF EXISTS congregation_contact_persons;
-- DROP TABLE IF EXISTS congregation_service_times;
-- DROP TABLE IF EXISTS congregation_addresses;
