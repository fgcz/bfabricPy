Feature: Redirect URL scheme handling
  As a web application behind a HTTPS proxy
  I want redirects to preserve the external protocol (HTTPS)
  So that users are not redirected to insecure URLs

  Background:
    Given the application is configured with auth middleware

  Scenario: Relative redirect is preserved as relative (browser resolves using proxy scheme)
    When I authenticate with proxy headers "X-Forwarded-Proto: https" and host "example.com"
    Then the redirect location should be "/"

  Scenario: Relative redirect uses HTTP when X-Forwarded-Proto indicates HTTP
    When I authenticate with proxy headers "X-Forwarded-Proto: http" and host "example.com"
    Then the redirect location should be "/"

  Scenario: Absolute redirect URL is preserved as-is
    Given the application is configured with authenticated_path "https://other.example.com/dashboard"
    When I authenticate with proxy headers "X-Forwarded-Proto: http" and host "example.com"
    Then the redirect location should be "https://other.example.com/dashboard"

  Scenario: Relative redirect with custom authenticated_path
    Given the application is configured with authenticated_path "/custom"
    When I authenticate with proxy headers "X-Forwarded-Proto: https" and host "example.com"
    Then the redirect location should be "/custom"
