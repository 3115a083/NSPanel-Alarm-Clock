"""Build an experimental clock view in the pinned Easy EU HMI; never build/flash TFT."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
BACKUP = 0x80000


def u32(data, offset=0):
    return struct.unpack_from('<I', data, offset)[0]


def crc_table():
    result = []
    for byte in range(256):
        value = byte << 24
        for _ in range(8):
            value = ((value << 1) ^ (0x04c11db7 if value & 0x80000000 else 0)) & 0xffffffff
        result.append(value)
    return result


TABLE = crc_table()


def checksum(data, seed=0xffffffff, stride=1):
    if len(data) % stride:
        raise ValueError('Unaligned checksum input')
    value = seed
    for offset in range(0, len(data), stride):
        value ^= int.from_bytes(data[offset:offset + stride], 'little')
        for _ in range(4):
            value = ((value << 8) & 0xffffffff) ^ TABLE[value >> 24]
    return value


def page_checksum(data):
    value = 0xffffffff
    for part in (data[4:], data[4:8], data[12:16], data[20:21], data[21:22]):
        value = checksum(part, value)
    return value


def directory(data):
    count = u32(data)
    end = 4 + 28 * count
    if end + 4 > min(BACKUP, len(data)):
        raise ValueError('Invalid directory size')
    if data[0x6ffff8:0x700000] != b'ver21234':
        raise ValueError('Unsupported HMI format')
    if data[:end + 4] != data[BACKUP:BACKUP + end + 4]:
        raise ValueError('Directory backup differs')
    if checksum(data[:end] + b'ADEC', stride=4) != u32(data, end):
        raise ValueError('Directory checksum differs')
    entries = []
    for index in range(count):
        off = 4 + 28 * index
        name, start, size, deleted = struct.unpack_from('<16sIIB', data, off)
        if deleted:
            continue
        if start + size > len(data):
            raise ValueError('Truncated resource')
        entries.append((off, name.split(b'\0')[0].decode('ascii'), start, size))
    return entries


def read_component(data):
    values = []
    offset = 0
    while offset < len(data):
        length = u32(data, offset)
        offset += 4
        if offset + length > len(data):
            raise ValueError('Truncated component record')
        values.append(data[offset:offset + length])
        offset += length
    if not values or values.pop() != b'':
        raise ValueError('Missing component terminator')
    groups = {}
    offset = 0
    while offset < len(values):
        name, count = values[offset].rsplit(b'-', 1)
        count = int(count)
        if name in groups or offset + 1 + count > len(values):
            raise ValueError('Invalid component group')
        groups[name] = values[offset + 1:offset + 1 + count]
        offset += 1 + count
    return groups


def write_component(groups):
    records = []
    for name, values in groups.items():
        records.append(name + b'-' + str(len(values)).encode())
        records.extend(values)
    records.append(b'')
    return b''.join(struct.pack('<I', len(value)) + value for value in records)


def attribute(groups, name):
    key = name.encode().ljust(16, b'\0')
    hits = [item[16:] for item in groups[b'att'] if item[:16] == key]
    if len(hits) != 1:
        raise ValueError('Missing/duplicate attribute: ' + name)
    return hits[0]


def set_attribute(groups, name, value):
    old = attribute(groups, name)
    if isinstance(value, int):
        value = value.to_bytes(len(old), 'little')
    elif isinstance(value, str):
        value = value.encode('ascii')
    key = name.encode().ljust(16, b'\0')
    groups[b'att'] = [key + value if item[:16] == key else item for item in groups[b'att']]


def read_page(data):
    if len(data) < 56 or u32(data, 4) != len(data) or u32(data, 8) != 56:
        raise ValueError('Unsupported page header')
    if page_checksum(data) != u32(data):
        raise ValueError('Page checksum differs')
    count = u32(data, 12)
    result = []
    expected = count * 12
    for index in range(count):
        start, size, reserved = struct.unpack_from('<III', data, 56 + 12 * index)
        # Nextion2Text confirms offsets are relative to the 56-byte header.
        if start != expected or reserved != 0:
            raise ValueError('Unsupported page component layout')
        raw = data[56 + start:56 + start + size]
        groups = read_component(raw)
        if write_component(groups) != raw:
            raise ValueError('Component round-trip differs')
        result.append(groups)
        expected += size
    if 56 + expected != len(data):
        raise ValueError('Unparsed page tail')
    return result


def write_page(original, components):
    records = [write_component(item) for item in components]
    header = bytearray(original[:56])
    struct.pack_into('<I', header, 12, len(records))
    offset = 12 * len(records)
    table = bytearray()
    for record in records:
        table.extend(struct.pack('<III', offset, len(record), 0))
        offset += len(record)
    page = header + table + b''.join(records)
    struct.pack_into('<I', page, 4, len(page))
    struct.pack_into('<I', page, 0, page_checksum(page))
    return bytes(page)


def inspect(path):
    raw = Path(path).read_bytes()
    entries = directory(raw)
    for _, name, start, size in entries:
        if name.endswith('.pa') and raw[start + 24:start + 40].split(b'\0')[0] == b'home_smpl':
            page = raw[start:start + size]
            components = read_page(page)
            for component in components:
                attrs = {item[:16].split(b'\0')[0].decode(): item[16:] for item in component[b'att']}
                print(attrs['objname'].decode(), {key: int.from_bytes(value, 'little')
                    for key, value in attrs.items() if key in ('type','id','sta','font','pco','bco','pic','picc','en')})
            return
    raise ValueError('Missing home_smpl')


# Coordinates are native EU pixels. Initial values deliberately do not show a
# fabricated time or armed plan before a matching firmware renderer is present.
LAYOUT = [
    ('wa_bg', '', 0, 0, 480, 320, 0, 65535, 0),
    ('wa_title', 'ALARM CLOCK', 20, 8, 270, 30, 2, 52857, 0),
    ('wa_state', 'Waiting...', 300, 8, 160, 30, 2, 52857, 2),
    ('wa_time', '--:--', 20, 44, 440, 94, 6, 65535, 1),
    ('wa_date', 'Waiting for firmware', 20, 140, 440, 30, 2, 52857, 1),
    ('wa_label', 'ALARM TIME', 20, 190, 230, 26, 1, 52857, 0),
    ('wa_alarm', '--:--', 20, 216, 200, 48, 5, 65535, 0),
    ('wa_enabled', 'Unknown', 280, 216, 180, 36, 3, 52857, 2),
    ('wa_days', 'No plan received', 20, 282, 440, 26, 1, 52857, 0),
]


def make_clock_page(original):
    components = read_page(original)
    by_name = {attribute(c, 'objname').decode(): c for c in components}
    if set(by_name) != {'home_smpl','swipe','swipestore','time','outdoor_temp','date',
            'weather','left_bt_text','right_bt_text','wifi_icon','lastclick',
            'settings_timer','click_comp','click_timer','bt_icon','b0','b1','b2',
            'b3','indr_temp','indr_temp_icon','meridiem'}:
        raise ValueError('Unexpected base components')
    template = copy.deepcopy(by_name['date'])
    hidden = []
    for c in components:
        name = attribute(c, 'objname').decode()
        kind = int.from_bytes(attribute(c, 'type'), 'little')
        for group in list(c):
            if group != b'att':
                c[group] = []  # No inherited touch/navigation actions on clock view.
        if kind == 51:
            set_attribute(c, 'en', 0)
        elif kind in (116, 112, 98):
            hidden.append(name)
    page = components[0]
    set_attribute(page, 'sta', 1)
    set_attribute(page, 'bco', 0)
    for name, text, x, y, width, height, font, color, align in LAYOUT:
        clone = copy.deepcopy(template)
        for group in list(clone):
            if group != b'att':
                clone[group] = []
        values = {'id': len(components), 'objname': name, 'sta': 1,
            'bco': 0, 'pco': color, 'font': font, 'txt': text, 'txt_maxl': 48,
            'x': x, 'y': y, 'w': width, 'h': height,
            'endx': x + width - 1, 'endy': y + height - 1,
            'xcen': align, 'ycen': 1, 'sendkey': 0}
        for attr, value in values.items():
            set_attribute(clone, attr, value)
        components.append(clone)
    page[b'codesload'] = [line.encode() for line in [
        'dim=brightness', 'back_page_id=home_page_id',
        *['vis ' + name + ',0' for name in hidden],
        'sendme', 'printh 93',
        'prints "wa_clock_v2",0', 'printh 00 01 FF FF FF',
    ]]
    return write_page(original, components)


def build(source):
    manifest = json.loads((ROOT / 'hmi/upstream.json').read_text(encoding='utf-8'))
    expected = manifest['files'][0]['sha256']
    if hashlib.sha256(source).hexdigest() != expected:
        raise ValueError('Only the pinned, unmodified EU source is supported')
    entries = directory(source)
    targets = {source[e[2]+24:e[2]+40].split(b'\0')[0]: e for e in entries
               if e[1].endswith('.pa')}
    if b'home_smpl' not in targets or b'boot' not in targets:
        raise ValueError('Missing clock or boot resource')
    result = bytearray(source)
    changed = set()
    for page_name in (b'home_smpl', b'boot'):
        off, name, start, size = targets[page_name]
        original = source[start:start + size]
        if page_name == b'home_smpl':
            replacement = make_clock_page(original)
            patched = read_page(replacement)
        else:
            components = read_page(original)
            timer = next(c for c in components if attribute(c, 'objname') == b'tm_display_ack')
            # Repeats until communication is ready, even without Wi-Fi/HA.
            # Preserve the complete original acknowledgement event.
            timer[b'codestimer'] = timer[b'codestimer'] + [b'printh 93',
                b'prints "wa_hmi_v2",0', b'printh 00 01 FF FF FF']
            replacement = write_page(original, components)
        new_start = len(result)
        result.extend(replacement)
        struct.pack_into('<II', result, off + 16, new_start, len(replacement))
        result[BACKUP + off:BACKUP + off + 28] = result[off:off + 28]
        changed.add(name)
    end = 4 + 28 * u32(result)
    crc = checksum(result[:end] + b'ADEC', stride=4)
    struct.pack_into('<I', result, end, crc)
    struct.pack_into('<I', result, BACKUP + end, crc)
    output_entries = directory(result)
    for entry, after in zip(entries, output_entries):
        _, old_name, old_start, old_size = entry
        _, new_name, new_offset, new_size = after
        if old_name != new_name:
            raise ValueError('Resource order changed')
        if old_name not in changed and source[old_start:old_start + old_size] != result[new_offset:new_offset + new_size]:
            raise ValueError('Unrelated resource changed: ' + old_name)
    if [attribute(c, 'objname').decode() for c in patched[-len(LAYOUT):]] != [row[0] for row in LAYOUT]:
        raise ValueError('Clock components did not round-trip')
    return bytes(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        if args.source.resolve() == args.output.resolve():
            raise ValueError('Never overwrite source HMI')
        data = build(args.source.read_bytes())
        if args.output.exists() and args.output.read_bytes() != data:
            raise ValueError('Existing working file differs; choose a new output name')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(data)
        print('Experimental HMI:', args.output)
        print('SHA-256:', hashlib.sha256(data).hexdigest())
        print('Page home_smpl contains the clock preview. Editor compile still required. Do not flash.')
    else:
        inspect(args.source)
