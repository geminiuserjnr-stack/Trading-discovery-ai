# Channel-Centric Migration Architecture

## Objective

Transform Trading-discovery-ai from a video/transcript-first discovery pipeline into a channel-centric Trading Community Discovery Engine.

The product goal is to discover high-quality trading YouTube channels, investigate whether they operate Discord communities, verify communities, and improve discovery through learned intelligence.

## Current Architecture Direction

Current flow:

Search Query -> YouTube Videos -> Transcript Extraction -> Phrase Extraction -> Query Generation

Problems:
- Videos become the product entity.
- Processing cost increases unnecessarily.
- Intelligence is optimized around content instead of communities.
- Weak community discovery capability.

## Target Architecture

Country Intelligence
-> Query Intelligence Engine
-> YouTube Channel Discovery
-> Channel Normalization
-> Channel Investigation Engine
-> Discord Verification
-> Channel Intelligence Record
-> Learning Loop

## Core Design Principles

1. Channel is the primary intelligence entity.
2. Videos and transcripts are evidence only.
3. Community discovery is the main success metric.
4. Discord links require verification.
5. Migration must be incremental and production-safe.

## Phase Plan

Phase 0: Safety preparation and documentation.
Phase 1: Database refactor.
Phase 2: Channel-first discovery pipeline.
Phase 3: Investigation engine.
Phase 4: Adaptive investigation policy.
Phase 5: Intelligence learning loop.
Phase 6: Dashboard migration.

## Migration Rules

- Do not delete legacy structures immediately.
- Detach old dependencies before removal.
- Avoid fixed investigation depth assumptions.
- Prevent duplicate channel records.
