# App Definition Design

## Goals

- Centralized configuration for all app versions so that if necessary adaptions to the system integration can be done in one place easily.

## Open question

## Future possibilities

- Version ranges: Maybe we could use semver, but it would need to be a standardized flavor thereof.
- Allow to provide a folder (or set of YAML files) with multiple app definitions, to be pooled together.
    If there are any version conflicts an error should be raised.
    There probably should be a tool to check the available versions easily.
