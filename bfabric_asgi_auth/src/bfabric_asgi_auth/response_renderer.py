"""Response rendering for authentication middleware.

This module provides a minimal protocol for customizing responses from the authentication middleware.
Users only need to implement two methods: render_error and render_redirect.
"""

from __future__ import annotations

from typing import Protocol

from asgiref.typing import ASGIReceiveCallable, ASGISendCallable, Scope


class ErrorContext:
    """Context information for error responses.

    :ivar message: The error message to display
    :ivar status_code: HTTP status code (400, 401, 500, etc.)
    :ivar error_type: Type of error ("missing_token", "invalid_token", "unauthorized", "server_error")
    :ivar scope: ASGI scope dictionary
    """

    def __init__(self, message: str, status_code: int, error_type: str, scope: Scope) -> None:
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.scope = scope


class RedirectContext:
    """Context information for redirect responses.

    :ivar url: The URL to redirect to
    :ivar redirect_type: Type of redirect ("authenticated", "other")
    :ivar scope: ASGI scope dictionary
    """

    def __init__(self, url: str, redirect_type: str, scope: Scope) -> None:
        self.url = url
        self.redirect_type = redirect_type
        self.scope = scope


class SuccessContext:
    """Context information for success responses.

    :ivar message: The success message to display
    :ivar success_type: Type of success ("logout", "other")
    :ivar scope: ASGI scope dictionary
    """

    def __init__(self, message: str, success_type: str, scope: Scope) -> None:
        self.message = message
        self.success_type = success_type
        self.scope = scope


class ResponseRenderer(Protocol):
    """Protocol for rendering authentication middleware responses.

    Implement this protocol to customize how the middleware renders responses.
    You only need to implement three methods: render_error, render_redirect, and render_success.
    """

    async def render_error(self, context: ErrorContext, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        """Render an error response.

        :param context: Error context with message, status code, and error type
        :param receive: ASGI receive callable
        :param send: ASGI send callable
        """
        ...

    async def render_redirect(
        self, context: RedirectContext, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        """Render a redirect response.

        :param context: Redirect context with URL and redirect type
        :param receive: ASGI receive callable
        :param send: ASGI send callable
        """
        ...

    async def render_success(
        self, context: SuccessContext, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        """Render a success response.

        :param context: Success context with message and success type
        :param receive: ASGI receive callable
        :param send: ASGI send callable
        """
        ...


class PlainTextRenderer:
    """Default plain text renderer.

    Renders all responses as plain text with appropriate status codes.
    """

    async def render_error(self, context: ErrorContext, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        """Render plain text error response."""
        from starlette.responses import PlainTextResponse

        response = PlainTextResponse(f"Error: {context.message}\n", status_code=context.status_code)
        await response(context.scope, receive, send)

    async def render_redirect(
        self, context: RedirectContext, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        """Render HTTP redirect response."""
        from starlette.responses import RedirectResponse

        response = RedirectResponse(url=context.url, status_code=302)
        await response(context.scope, receive, send)

    async def render_success(
        self, context: SuccessContext, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        """Render plain text success response."""
        from starlette.responses import PlainTextResponse

        response = PlainTextResponse(f"{context.message}\n", status_code=200)
        await response(context.scope, receive, send)


class HTMLRenderer:
    """Self-contained HTML renderer with inline CSS.

    Renders errors as styled HTML pages with no external dependencies.

    :ivar page_title: Title for the HTML page
    :ivar show_error_details: Whether to show detailed error information
    """

    def __init__(self, page_title: str = "Authentication", show_error_details: bool = True) -> None:
        self.page_title = page_title
        self.show_error_details = show_error_details

    async def render_error(self, context: ErrorContext, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        """Render self-contained HTML error page."""
        from starlette.responses import HTMLResponse

        # Map status codes to user-friendly titles
        title_map = {
            400: "Bad Request",
            401: "Unauthorized",
            500: "Server Error",
        }
        title = title_map.get(context.status_code, "Error")

        # Optionally show detailed error type
        details = (
            f"<p style='color: #666; font-size: 0.9em; margin-top: 1em;'>Error type: {context.error_type}</p>"
            if self.show_error_details
            else ""
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} - {self.page_title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
            padding: 2rem;
        }}
        .container {{
            max-width: 600px;
            margin: 4rem auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            padding: 3rem;
            text-align: center;
        }}
        .icon {{
            color: #dc3545;
            margin-bottom: 1.5rem;
        }}
        h1 {{
            font-size: 1.75rem;
            margin-bottom: 1rem;
            color: #212529;
        }}
        p {{
            font-size: 1.1rem;
            color: #495057;
            margin-bottom: 0.5rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" fill="currentColor" viewBox="0 0 16 16">
                <path d="M7.938 2.016A.13.13 0 0 1 8.002 2a.13.13 0 0 1 .063.016.146.146 0 0 1 .054.057l6.857 11.667c.036.06.035.124.002.183a.163.163 0 0 1-.054.06.116.116 0 0 1-.066.017H1.146a.115.115 0 0 1-.066-.017.163.163 0 0 1-.054-.06.176.176 0 0 1 .002-.183L7.884 2.073a.147.147 0 0 1 .054-.057zm1.044-.45a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566z"/>
                <path d="M7.002 12a1 1 0 1 1 2 0 1 1 0 0 1-2 0zM7.1 5.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995z"/>
            </svg>
        </div>
        <h1>{title}</h1>
        <p>{context.message}</p>
        {details}
    </div>
</body>
</html>"""
        response = HTMLResponse(html, status_code=context.status_code)
        await response(context.scope, receive, send)

    async def render_redirect(
        self, context: RedirectContext, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        """Render HTTP redirect response."""
        from starlette.responses import RedirectResponse

        response = RedirectResponse(url=context.url, status_code=302)
        await response(context.scope, receive, send)

    async def render_success(
        self, context: SuccessContext, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        """Render self-contained HTML success page."""
        from starlette.responses import HTMLResponse

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Success - {self.page_title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
            padding: 2rem;
        }}
        .container {{
            max-width: 600px;
            margin: 4rem auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            padding: 3rem;
            text-align: center;
        }}
        .icon {{
            color: #28a745;
            margin-bottom: 1.5rem;
        }}
        h1 {{
            font-size: 1.75rem;
            margin-bottom: 1rem;
            color: #212529;
        }}
        p {{
            font-size: 1.1rem;
            color: #495057;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" fill="currentColor" viewBox="0 0 16 16">
                <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                <path d="M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05z"/>
            </svg>
        </div>
        <h1>Success</h1>
        <p>{context.message}</p>
    </div>
</body>
</html>"""
        response = HTMLResponse(html, status_code=200)
        await response(context.scope, receive, send)
