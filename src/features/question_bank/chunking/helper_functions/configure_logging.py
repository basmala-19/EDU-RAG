import logging
def configure_logging(
    level: int = logging.INFO,
) -> None:
    """
    Configure logging for standalone execution.

    If this module is imported by another application, the
    application can configure logging itself instead.
    """

    logging.basicConfig(
        level=level,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
    )