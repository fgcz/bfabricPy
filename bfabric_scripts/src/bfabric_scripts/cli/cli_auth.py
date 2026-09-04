import cyclopts

from bfabric_scripts.cli.login.manage import (
    cmd_auth_activate,
    cmd_auth_list,
    cmd_auth_logout,
    cmd_auth_remove,
    cmd_auth_status,
)
from bfabric_scripts.cli.login.oauth_login import cmd_auth_device_code, cmd_auth_login
from bfabric_scripts.cli.login.pat import cmd_auth_pat
from bfabric_scripts.cli.login.register import cmd_login_register
from bfabric_scripts.cli.login.register_webapp import cmd_login_register_webapp

cmd_auth = cyclopts.App(help="Authentication commands for B-Fabric.")
_ = cmd_auth.command(cmd_auth_pat, name="pat")
_ = cmd_auth.command(cmd_auth_login, name="login")
_ = cmd_auth.command(cmd_auth_device_code, name="device-code")
_ = cmd_auth.command(cmd_login_register, name="register")
_ = cmd_auth.command(cmd_login_register_webapp, name="register-webapp")
_ = cmd_auth.command(cmd_auth_status, name="status")
_ = cmd_auth.command(cmd_auth_logout, name="logout")
_ = cmd_auth.command(cmd_auth_remove, name="remove")
_ = cmd_auth.command(cmd_auth_activate, name="activate")
_ = cmd_auth.command(cmd_auth_list, name="list")
