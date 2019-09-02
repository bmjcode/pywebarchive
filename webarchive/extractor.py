"""The deprecated Extractor class."""


__all__ = ["Extractor"]


def Extractor(archive):
    """Do not use. Functionality moved to WebArchive.extract().

    This is present to maintain backwards compatibility with the
    poorly-thought-out API in version 0.1.0, the first public release.
    """

    return archive
