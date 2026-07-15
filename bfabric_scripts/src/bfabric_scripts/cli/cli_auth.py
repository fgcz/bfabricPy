import cyclopts

from bfabric_scripts.cli.login.default_config import cmd_auth_default
from bfabric_scripts.cli.login.device_code import cmd_login_device_code
from bfabric_scripts.cli.login.list import cmd_auth_list
from bfabric_scripts.cli.login.logout import cmd_login_logout
from bfabric_scripts.cli.login.pat import cmd_login_pat
from bfabric_scripts.cli.login.pkce import cmd_login_pkce
from bfabric_scripts.cli.login.register import cmd_login_register
from bfabric_scripts.cli.login.register_webapp import cmd_login_register_webapp
from bfabric_scripts.cli.login.status import cmd_login_status

cmd_auth = cyclopts.App(help="Authentication commands for B-Fabric.")
_ = cmd_auth.command(cmd_login_pat, name="pat")
_ = cmd_auth.command(cmd_login_pkce, name="pkce")
_ = cmd_auth.command(cmd_login_device_code, name="device-code")
_ = cmd_auth.command(cmd_login_register, name="register")
_ = cmd_auth.command(cmd_login_register_webapp, name="register-webapp")
_ = cmd_auth.command(cmd_login_status, name="status")
_ = cmd_auth.command(cmd_login_logout, name="logout")
_ = cmd_auth.command(cmd_auth_default, name="default")
_ = cmd_auth.command(cmd_auth_list, name="list")
