"""The one exception uc-portage raises for anything it refuses to do."""


class PortageError(Exception):
    """An offering, a state file or a target that uc-portage will not act on.

    The command line turns it into a message and exit status 1; a caller
    using the library, such as uc-automa, catches it.
    """
