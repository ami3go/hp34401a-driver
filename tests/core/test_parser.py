"""Parser tests (spec section 29.2)."""

import pytest

from hp34401a_dmm import parser
from hp34401a_dmm.errors import ProtocolError


def test_parse_positive_float():
    assert parser.parse_float("+1.23456789E+00") == pytest.approx(1.23456789)


def test_parse_negative_small_float():
    assert parser.parse_float("-1.23456789E-03") == pytest.approx(-1.23456789e-3)


def test_overload_classification():
    val = parser.parse_float("9.90000000E+37")
    assert parser.is_overload(val)


def test_no_error_response():
    parsed = parser.parse_error('+0,"No error"')
    assert parser.is_no_error(parsed)
    assert parsed.code == 0


def test_undefined_header_error():
    parsed = parser.parse_error('-113,"Undefined header"')
    assert parsed.code == -113
    assert parsed.message == "Undefined header"


def test_query_interrupted_error():
    parsed = parser.parse_error('-410,"Query interrupted"')
    assert parsed.code == -410


def test_comma_separated_fetch():
    vals = parser.parse_reading_list("+1.0E+00,+2.0E+00,+3.0E+00")
    assert vals == [1.0, 2.0, 3.0]


def test_empty_response_raises():
    with pytest.raises(ProtocolError):
        parser.parse_reading_list("")


def test_partial_response_raises():
    with pytest.raises(ProtocolError):
        parser.parse_reading_list("+1.0E+00,not-a-number")


def test_crlf_termination():
    assert parser.parse_float("+1.0E+00\r\n") == pytest.approx(1.0)


def test_lf_termination():
    assert parser.parse_float("+1.0E+00\n") == pytest.approx(1.0)


def test_malformed_error_raises():
    with pytest.raises(ProtocolError):
        parser.parse_error("not an error response")


def test_identity_parsing_normalizes_serial_zero():
    man, model, serial, fw = parser.parse_identity("HEWLETT-PACKARD,34401A,0,11-05-01")
    assert man == "HEWLETT-PACKARD"
    assert model == "34401A"
    assert serial is None
    assert fw == "11-05-01"


def test_looks_like_34401a():
    assert parser.looks_like_34401a("HEWLETT-PACKARD,34401A,0,11-05-01")
    assert not parser.looks_like_34401a("")
    assert not parser.looks_like_34401a("garbage\x00\xff bytes")


def test_trailing_comma_partial_response_raises():
    with pytest.raises(ProtocolError):
        parser.parse_reading_list("+1.0E+00,")


def test_empty_middle_field_partial_response_raises():
    with pytest.raises(ProtocolError):
        parser.parse_reading_list("+1.0E+00,,+2.0E+00")
