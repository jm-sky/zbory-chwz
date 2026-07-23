-- Migration: Add status column to tenants table
-- This migration adds status column to the tenants table to support
-- draft/published status for congregations.

-- Upgrade: Add status column
ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'draft';

-- Downgrade: Remove status column
-- ALTER TABLE tenants
-- DROP COLUMN IF EXISTS status;
