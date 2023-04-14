import cmd
import logging
import readline
import traceback
from aws import *
from _api import *
from typing import Optional


class InvisinetShell(cmd.Cmd):
    intro = """    ____           _      _            __      
   /  _/___ _   __(_)____(_)___  ___  / /______
   / // __ \ | / / / ___/ / __ \/ _ \/ __/ ___/
 _/ // / / / |/ / (__  ) / / / /  __/ /_(__  ) 
/___/_/ /_/|___/_/____/_/_/ /_/\___/\__/____/  
                                               
"""

    @property
    def prompt(self):
        if self.deployment is None:
            return f"(invisinet-{self.provider}) "
        else:
            return f"(invisinet-{self.provider}-{self.deployment.deployment_id}) "
    deployment: Optional[Invisinet] = None
    provider: str = "aws"

    def do_provider(self, arg):
        assert arg in {"aws", "azure", "gcp"}, f"Unsupported provider f{arg}"
        self.provider = arg

    @property
    def provider_cls(self):
        if self.provider == "aws":
            return InvisinetAWS

    def do_deployment(self, arg):
        """List all existing deployments in AWS, Azure, or GCP"""
        args = parse(arg)
        if args[0] == "list":
            deployment_ids = list(map(lambda x: x.deployment_id,
                                      self.provider_cls.list_deployments()))
            print(f"Existing deployment IDs for AWS: "
                  f"{', '.join(deployment_ids)}")
        elif args[0] == "new":
            self.deployment = self.provider_cls()
        elif args[0] == "load":
            self.deployment = self.provider_cls(args[1])

    def do_request_eip(self, arg):
        self.deployment.request_eip(*parse(arg))

    def do_request_sip(self, arg):
        self.deployment.request_sip(*parse(arg))

    def do_bind(self, arg):
        self.deployment.bind(*parse(arg))

    def do_annotate(self, arg):
        self.deployment.annotate(*parse(arg))

    def onecmd(self, line):
        try:
            return super().onecmd(line)
        except Exception as e:
            print(traceback.format_exc())
            return False  # don't stop


def parse(arg):
    return tuple(arg.split())


if __name__ == '__main__':
    logging.basicConfig(level="INFO")
    InvisinetShell().cmdloop()
