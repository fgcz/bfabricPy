# App Definition Design

## Goals

- Centralized configuration for all app versions so that if necessary adaptions to the system integration can be done in one place easily.

## Remarks

- The app ID is not part of the app specification, since the same app specification can be used for multiple B-Fabric apps.

## Open question

## Future possibilities

- Version ranges: Maybe we could use semver, but it would need to be a standardized flavor thereof.
- Allow to provide a folder (or set of YAML files) with multiple app definitions, to be pooled together.
    If there are any version conflicts an error should be raised.
    There probably should be a tool to check the available versions easily.
