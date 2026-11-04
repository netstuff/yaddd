# Infrastructure layer

Additive to the core rules. Never relaxes core rules; on conflict, core wins.

- **Implements ports** declared by `domain` and `application`; never invents
  new vocabulary for the domain.
- **Owns adapters** for persistence, messaging, external services, probes,
  settings and logging.
- **Validate at the boundary.** Values entering and leaving a store use the VO
  type, so validation happens on the way in and on the way out.
- **Identifiers live in `infrastructure/*/constants.py`:** table names, payload
  keys, channel names, config defaults.
- **Wiring:** construct adapters here; register them in the composition root,
  not in layer modules.
