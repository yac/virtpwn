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
