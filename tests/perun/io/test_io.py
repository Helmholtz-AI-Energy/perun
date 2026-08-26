import pytest

from perun.io.io import IOFormat


@pytest.mark.parametrize(
    "suffix, expected",
    [
        ("txt", IOFormat.TEXT),
        (".txt", IOFormat.TEXT),
        ("HDF5", IOFormat.HDF5),
        (".hdf5", IOFormat.HDF5),
        ("pkl", IOFormat.PICKLE),
        ("csv", IOFormat.CSV),
        # "json" is shared by JSON and BENCH; the first registered match wins.
        ("json", IOFormat.JSON),
    ],
)
def test_from_suffix_valid(suffix, expected):
    assert IOFormat.fromSuffix(suffix) == expected


def test_from_suffix_invalid():
    with pytest.raises(ValueError):
        IOFormat.fromSuffix("not_a_format")


def test_from_suffix_is_exact_not_substring():
    """A suffix like ``txt`` must not accidentally match unrelated formats."""
    # "t" is a substring of several suffixes; ensure it does not resolve.
    with pytest.raises(ValueError):
        IOFormat.fromSuffix("t")


def test_suffix_roundtrip():
    for fmt in IOFormat:
        assert IOFormat(fmt.value).suffix == fmt.suffix
