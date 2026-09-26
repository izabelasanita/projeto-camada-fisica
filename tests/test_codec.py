import pytest

from camada_fisica.codec import (
    bits_to_bytes,
    bytes_to_bits,
    bytes_to_text,
    text_to_bytes,
)


def test_text_to_bytes():
    assert text_to_bytes("A") == b"A"


def test_bytes_to_bits():
    assert bytes_to_bits(b"A") == [0, 1, 0, 0, 0, 0, 0, 1]


def test_bits_to_bytes():
    bits = [0, 1, 0, 0, 0, 0, 0, 1]

    assert bits_to_bytes(bits) == b"A"


def test_text_round_trip():
    original = "Olá, mundo!"

    data = text_to_bytes(original)
    bits = bytes_to_bits(data)
    reconstructed_data = bits_to_bytes(bits)
    reconstructed_text = bytes_to_text(reconstructed_data)

    assert reconstructed_text == original


def test_bits_must_have_complete_bytes():
    with pytest.raises(ValueError):
        bits_to_bytes([0, 1, 0])


def test_bits_must_be_zero_or_one():
    with pytest.raises(ValueError):
        bits_to_bytes([0, 1, 2, 0, 0, 0, 0, 1])