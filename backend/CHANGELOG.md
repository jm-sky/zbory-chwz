# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.12.0] - 2025-11-25

### Added
- S3 storage support with Scaleway Object Storage integration
- Storage CLI command for testing S3 connectivity
  - `storage info` - Display current storage configuration
  - `storage test` - Test upload/download/delete operations
- S3 environment variables in production docker-compose.yml
- Support for Scaleway Object Storage (Warsaw region: pl-waw)

### Changed
- Storage adapter automatically switches between local and S3 based on `STORAGE_TYPE` environment variable
- Image uploads now use configured storage backend (local or S3)

## [2.11.1] - 2024-11-24

### Changed
- Previous changes (see git history)
