def build(bytecode, type='exec'):
    pex = []

    magic = b'PEX'
    pex.append(magic)
    encoded_type = ['other', 'exec', 'lib'].index(type)
    pex.append(bytes([encoded_type]))
    
    format_version = b'\x00\x00\x00\x00'
    pex.append(format_version)

    section_count = (1).to_bytes(8, 'big')
    pex.append(section_count)

    assert len(b''.join(pex)) == 16
    section = []
    section.append(b'code')
    section.append(bytecode)
    section_bytes = b''.join(section)
    pex.append(len(section_bytes).to_bytes(8, 'big'))
    pex.append(section_bytes)
    return b''.join(pex)
