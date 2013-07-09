import const


class PwnException(Exception):
    message = "An unknown error occurred."

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs
        if not message:
            try:
                message = self.message % kwargs
            except Exception as e:
                # kwargs doesn't mach those in message.
                # Returning this is still better than nothing.
                message = self.message
        super(PwnException, self).__init__(message)


class ProjectConfigNotFound(PwnException):
    message = "Couldn't find any project configuration file {%s}" % \
              ", ".join(const.CONF_FNS)

class MissingRequiredConfigOption(PwnException):
    message = "Config is missing required option %(option)s"


class CommandFailed(PwnException):
    message = "Running command failed: %(cmd)s"

    def __init__(self, **kwargs):
        self.cmd = kwargs.get('cmd')
        self.ret = kwargs.get('ret')
        self.out = kwargs.get('out')
        self.err = kwargs.get('err')
        super(CommandFailed, self).__init__(kwargs)


class Bug(RuntimeError):
    pass

class VirshParseError(PwnException):
    message = "Failed to parse virsh output: %(out)s"


class UnknownProvisioner(PwnException):
    message = "Unknown provision provider: %(provider)s"
