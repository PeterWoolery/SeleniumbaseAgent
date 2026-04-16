from src.mcp_server import session


def browser_solve_captcha() -> dict:
    """Attempt CAPTCHA solving using mode-appropriate method.

    CDP mode: sb.solve_captcha()
    UC mode:  sb.uc_gui_click_captcha()
    standard: no-op
    """
    return session.solve_captcha()
