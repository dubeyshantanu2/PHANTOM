# Changelog

All notable changes to the PHANTOM project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-18

### Added
- Initial release of PHANTOM (Price Hunt And Market Trap Observation Node).
- Core engines: Bias, Candle, Engine, FVG, Liquidity, Mode Controller, Setup Validator, Sweep Detector, and Target Resolver.
- Data integration with Dhan HQ API.
- Persistence layer using Supabase.
- Discord alerting system for session updates and trading setups.
- Multi-timeframe support (1m, 5m, 15m, 1h).
- Support for Indian markets (NSE + MCX).
- **Project Structure**: Comprehensive `.gitignore` to maintain a clean repository.

### Security
- Environment variable based configuration for sensitive API keys and secrets.
