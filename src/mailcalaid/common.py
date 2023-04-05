import platform
import os

def get_config_dir():
  if platform.system() == "Windows":
    return os.path.join(os.environ["LOCALAPPDATA"], "mailcalaid")
  return os.path.expanduser("~/.config/mailcalaid")
