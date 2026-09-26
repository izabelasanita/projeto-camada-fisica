def text_to_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def bytes_to_bits(data: bytes) -> list[int]:
    bits = []

    for byte in data:
        for position in range(7, -1, -1):
            bit = (byte >> position) & 1
            bits.append(bit)

    return bits


def bits_to_bytes(bits: list[int]) -> bytes:
    if len(bits) % 8 != 0:
        raise ValueError("A quantidade de bits deve ser múltipla de 8.")

    data = bytearray()

    for start in range(0, len(bits), 8):
        byte_bits = bits[start:start + 8]
        value = 0

        for bit in byte_bits:
            if bit not in (0, 1):
                raise ValueError("Cada bit deve ser 0 ou 1.")

            value = (value << 1) | bit

        data.append(value)

    return bytes(data)


def bytes_to_text(data: bytes) -> str:
    return data.decode("utf-8")