#!/usr/bin/env python3
"""Generate knob-base.kicad_sch (GaggiMate knob, Board A).

Circuit derived from SmartKnob View `electronics/view_base` (Scott Bezek,
Apache-2.0): MT6701 magnetic encoder under the motor, HX711 + four SMD-resistor
strain gauges on the PCB flexure. Everything else from view_base is removed and
the board is powered (3V3) and read through an 8-pin JST-SH from Board B.

Run with plain python3; writes ../knob-base.kicad_sch. Symbols are copied from
KiCad 10's bundled libraries. Each connected pin gets a short wire stub ending
in a net label or power symbol (no long wires), so the netlist is explicit.
"""
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
import json
import re

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'knob-base.kicad_sch'
LIB = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols')
NAME = 'knob-base'


def uid(text):
    return str(uuid5(NAMESPACE_URL, 'gaggimate/hardware/knob/pcb/knob-base/' + text))


ROOT = uid('root-sheet')


def q(v):
    return json.dumps(str(v))


def eff(size=1.27, hide=False, justify=''):
    return (f'(effects (font (size {size} {size}))' + (f' (justify {justify})' if justify else '')
            + (' (hide yes)' if hide else '') + ')')


_cache = {}


def symtext(lib, name):
    text = _cache.setdefault(lib, (LIB / (lib + '.kicad_sym')).read_text())
    start = text.index('\n\t(symbol "' + name + '"')
    end = text.find('\n\t(symbol ', start + 1)
    body = text[start:end if end != -1 else text.rfind('\n)')].lstrip('\n')
    assert '(extends' not in body, name
    return body.replace('(symbol "' + name + '"', '(symbol "' + lib + ':' + name + '"', 1)


def pins_of(body):
    out = {}
    for m in re.finditer(r'\(pin (\w+) \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)\s*\(length ([\d.]+)\)'
                         r'(?:\s*\(hide yes\))?\s*\(name "([^"]*)".*?\(number "([^"]*)"', body, re.S):
        kind, x, y, a, _l, _n, num = m.groups()
        out[num] = (float(x), float(y), int(a))
    return out


# ---------------------------------------------------------------- parts ----
# (ref, lib:symbol, value, x, y, footprint, LCSC, MPN, {pin: net}, [nc pins], extra)
FP_R0603 = 'Resistor_SMD:R_0603_1608Metric'
FP_C0603 = 'Capacitor_SMD:C_0603_1608Metric'
FP_C0805 = 'Capacitor_SMD:C_0805_2012Metric'
FP_R2512 = 'Resistor_SMD:R_2512_6332Metric'

PARTS = [
    # connector to Board B (pinout fixed by the design doc section 5)
    ('J1', 'Connector_Generic:Conn_01x08', 'JST-SH 8p to Board B', 30.48, 63.5,
     'Connector_JST:JST_SH_SM08B-SRSS-TB_1x08-1MP_P1.00mm_Horizontal', 'C160407', 'SM08B-SRSS-TB(LF)(SN)',
     {'1': '+3V3', '2': 'GND', '3': 'ENC_CS', '4': 'ENC_CLK', '5': 'ENC_DO', '6': 'HX_SCK',
      '7': 'HX_DOUT', '8': 'GND'}, [], {}),
    # magnetic encoder, exactly at board centre under the motor magnet
    ('U1', 'Sensor_Magnetic:MT6701CT', 'MT6701CT-STD-R', 83.82, 63.5,
     'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm', 'C3003196', 'MT6701CT-STD-R',
     {'1': '+3V3', '2': '+3V3', '4': 'GND', '6': 'ENC_DO', '7': 'ENC_CLK', '8': 'ENC_CS'}, ['3', '5'],
     {'Note': 'MODE=VDD selects SSI (as SmartKnob). Pins 6/7/8 = DO/CLK/CSN in SSI mode.'}),
    ('C20', 'Device:C', '100n', 116.84, 63.5, FP_C0603, 'C14663', 'CC0603KRX7R9BB104',
     {'1': '+3V3', '2': 'GND'}, [], {}),
    # HX711 load-cell ADC (80 SPS: RATE tied high, internal oscillator: XI to AGND)
    ('U4', 'Analog_ADC:HX711', 'HX711', 205.74, 63.5,
     'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm', 'C6705483', 'HX711',
     {'1': '+3V3', '2': 'HX_BASE', '3': 'HX_AVDD', '4': 'HX_VFB', '5': 'GNDA', '6': 'HX_VBG',
      '7': 'HX_INA-', '8': 'HX_INA+', '9': 'GNDA', '10': 'GNDA', '11': 'HX_SCK', '12': 'HX_DOUT',
      '14': 'GNDA', '15': '+3V3', '16': '+3V3'}, ['13'], {}),
    # AVDD regulator: PNP pass transistor, AVDD = 1.25 V * (R3+R4)/R4 = 2.77 V
    ('Q1', 'Transistor_BJT:Q_PNP_BEC', 'SS8550', 27.94, 132.08,
     'Package_TO_SOT_SMD:SOT-23', 'C8542', 'SS8550 Y2',
     {'1': 'HX_BASE', '2': '+3V3', '3': 'HX_AVDD'}, [], {}),
    ('R3', 'Device:R', '10k', 45.72, 132.08, FP_R0603, 'C25804', '0603WAF1002T5E',
     {'1': 'HX_AVDD', '2': 'HX_VFB'}, [], {}),
    ('R4', 'Device:R', '8.2k', 63.50, 132.08, FP_R0603, 'C25981', '0603WAF8201T5E',
     {'1': 'HX_VFB', '2': 'GNDA'}, [], {}),
    ('FB1', 'Device:FerriteBead', '100R@100MHz', 81.28, 132.08, 'Inductor_SMD:L_0805_2012Metric',
     'C1015', 'GZ2012D101TF', {'1': 'HX_AVDD', '2': 'BRIDGE_E+'}, [],
     {'Note': 'Replaces SmartKnob L1 (3.3uH, C307744, extended) with a JLC basic ferrite bead'}),
    ('C18', 'Device:C', '10u', 99.06, 132.08, FP_C0805, 'C15850', 'CL21A106KAYNNNE',
     {'1': 'BRIDGE_E+', '2': 'GNDA'}, [], {}),
    ('C19', 'Device:C', '100n', 116.84, 132.08, FP_C0603, 'C14663', 'CC0603KRX7R9BB104',
     {'1': 'BRIDGE_E+', '2': 'GNDA'}, [], {}),
    ('C22', 'Device:C', '100n', 134.62, 132.08, FP_C0603, 'C14663', 'CC0603KRX7R9BB104',
     {'1': 'GNDA', '2': 'HX_VBG'}, [], {}),
    ('R5', 'Device:R', '100', 152.40, 132.08, FP_R0603, 'C22775', '0603WAF1000T5E',
     {'1': 'HX_INA-', '2': 'BRIDGE_S-'}, [], {}),
    ('R6', 'Device:R', '100', 170.18, 132.08, FP_R0603, 'C22775', '0603WAF1000T5E',
     {'1': 'BRIDGE_S+', '2': 'HX_INA+'}, [], {}),
    ('C23', 'Device:C', '100n', 187.96, 132.08, FP_C0603, 'C14663', 'CC0603KRX7R9BB104',
     {'1': 'HX_INA+', '2': 'HX_INA-'}, [], {}),
    ('C12', 'Device:C', '100n', 205.74, 132.08, FP_C0603, 'C14663', 'CC0603KRX7R9BB104',
     {'1': '+3V3', '2': 'GNDA'}, [], {}),
    ('C16', 'Device:C', '10u', 223.52, 132.08, FP_C0805, 'C15850', 'CL21A106KAYNNNE',
     {'1': '+3V3', '2': 'GNDA'}, [], {}),
    # Wheatstone bridge of 2512 resistors used as strain gauges on the flexure arms
    ('R18', 'Device:R', '330 (strain)', 50.8, 177.8, FP_R2512, 'C19866', '25121WJ0331T4E',
     {'1': 'BRIDGE_E+', '2': 'BRIDGE_S+'}, [], {'Note': '+X arm, outer root'}),
    ('R19', 'Device:R', '330 (strain)', 66.04, 177.8, FP_R2512, 'C19866', '25121WJ0331T4E',
     {'1': 'BRIDGE_S+', '2': 'GNDA'}, [], {'Note': '+X arm, inner root'}),
    ('R20', 'Device:R', '330 (strain)', 81.28, 177.8, FP_R2512, 'C19866', '25121WJ0331T4E',
     {'1': 'BRIDGE_S-', '2': 'BRIDGE_E+'}, [], {'Note': '-X arm, inner root'}),
    ('R21', 'Device:R', '330 (strain)', 96.52, 177.8, FP_R2512, 'C19866', '25121WJ0331T4E',
     {'1': 'GNDA', '2': 'BRIDGE_S-'}, [], {'Note': '-X arm, outer root'}),
    # analog ground joins digital ground at one point, next to the HX711
    ('NT1', 'Device:NetTie_2', 'NetTie', 127.0, 177.8, 'NetTie:NetTie-2_SMD_Pad0.5mm', '', '',
     {'1': 'GNDA', '2': 'GND'}, [], {}),
]
POWER = {'+3V3': 'power:+3V3', 'GND': 'power:GND', 'GNDA': 'power:GNDA'}
# outward stub direction (sheet coords, Y down) from pin angle in the library
OUT_DIR = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}


def main():
    libs = sorted({p[1] for p in PARTS} | set(POWER.values()) | {'power:PWR_FLAG'})
    defs = {lid: symtext(*lid.split(':')) for lid in libs}
    pins = {lid: pins_of(d) for lid, d in defs.items()}
    s = [f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "10.0") (uuid "{ROOT}") (paper "A4")',
         '(title_block (title "GaggiMate knob - Board A knob-base") (date "2026-11-07") (rev "1")'
         ' (company "GaggiMate knob (personal fork)")'
         ' (comment 1 "Derived from SmartKnob View view_base by Scott Bezek, Apache-2.0")'
         ' (comment 2 "MT6701 encoder + HX711 strain-gauge press sensor; 3V3 from Board B via JST-SH 8p"))',
         '(lib_symbols ' + '\n'.join(defs.values()) + ')']
    n = [0]

    def nid(kind):
        n[0] += 1
        return uid(f'{kind}{n[0]}')

    def wire(x1, y1, x2, y2):
        s.append(f'(wire (pts (xy {x1:.2f} {y1:.2f}) (xy {x2:.2f} {y2:.2f})) (stroke (width 0) (type default)) (uuid "{nid("w")}"))')

    def text(t, x, y, size=1.27):
        s.append(f'(text {q(t)} (exclude_from_sim no) (at {x} {y} 0) {eff(size, justify="left top")} (uuid "{nid("t")}"))')

    def place(ref, lid, value, x, y, rot=0, fp='', lcsc='', mpn='', extra=None, bom=True, refpos=None, valpos=None):
        s.append(f'(symbol (lib_id {q(lid)}) (at {x:.2f} {y:.2f} {rot}) (unit 1) (exclude_from_sim no)'
                 f' (in_bom {"yes" if bom else "no"}) (on_board {"yes" if bom or ref.startswith("NT") else "no"})'
                 f' (dnp no) (uuid "{uid("sym-" + ref)}")')
        rx, ry = refpos or (x + 3.0, y - 2.0)
        hidden_ref = ref.startswith('#')
        vx, vy = valpos or (rx, ry + 2.54)
        props = [('Reference', ref, rx, ry, hidden_ref), ('Value', value, vx, vy, False),
                 ('Footprint', fp, x, y, True), ('Datasheet', '', x, y, True), ('Description', '', x, y, True)]
        if not ref.startswith('#'):
            props += [('LCSC', lcsc, x, y, True), ('MPN', mpn, x, y, True)]
        for k, v in (extra or {}).items():
            props.append((k, v, x, y, True))
        for k, v, px, py, hide in props:
            s.append(f'(property {q(k)} {q(v)} (at {px:.2f} {py:.2f} 0) {eff(1.27, hide, "left")})')
        s.append(f'(instances (project {q(NAME)} (path "/{ROOT}" (reference {q(ref)}) (unit 1)))))')

    pwr_n = [0]

    def power(net, x, y, d):
        pwr_n[0] += 1
        lid = POWER[net]
        up = net == '+3V3'
        # default body: +3V3 up, GND/GNDA down; rotate so body points along the stub direction d
        rot = {(0, -1): 0 if up else 180, (0, 1): 180 if up else 0,
               (-1, 0): 90 if up else 270, (1, 0): 270 if up else 90}[d]
        vx = x + d[0] * 4.2 + (0.6 if d[0] == 0 else 0) - (len(net) * 1.0 if d[0] < 0 else 0)
        vy = y + d[1] * 4.2 + (0.6 if d[1] == 0 else 0)
        place(f'#PWR{pwr_n[0]:03d}', lid, net, x, y, rot, bom=False, valpos=(vx, vy))

    def label(net, x, y, d):
        ang, just = {(-1, 0): (180, 'right bottom'), (1, 0): (0, 'left bottom'),
                     (0, -1): (90, 'left bottom'), (0, 1): (270, 'right bottom')}[d]
        s.append(f'(label {q(net)} (at {x:.2f} {y:.2f} {ang}) {eff(1.27, justify=just)} (uuid "{nid("l")}"))')

    for ref, lid, value, x, y, fp, lcsc, mpn, conns, nc, extra in PARTS:
        bom = not ref.startswith('NT')
        if ref.startswith('NT'):
            extra = dict(extra, **{'Note': 'Net tie: single GNDA/GND star point beside HX711 AGND (as SmartKnob NT1)'})
        place(ref, lid, value, x, y, 0, fp, lcsc, mpn, extra, bom=bom,
              refpos=None)
        for num, (px, py, a) in pins[lid].items():
            sx, sy = x + px, y - py
            if num in nc:
                s.append(f'(no_connect (at {sx:.2f} {sy:.2f}) (uuid "{nid("nc")}"))')
                continue
            net = conns.get(num)
            assert net, (ref, num)
            d = OUT_DIR[a]
            ex, ey = sx + d[0] * 2.54, sy + d[1] * 2.54
            wire(sx, sy, ex, ey)
            if net in POWER:
                power(net, ex, ey, d)
            else:
                label(net, ex, ey, d)
        assert set(conns) | set(nc) == set(pins[lid]), ref

    # power flags: the 3V3/GND rails come from Board B through J1; GNDA via net tie;
    # HX_AVDD is made by the PNP regulator (the HX711 AVDD pin is typed power-in).
    for i, net in enumerate(['+3V3', 'GND', 'GNDA', 'HX_AVDD']):
        x, y = 241.3 + (i % 2) * 20.32, 139.7 + (i // 2) * 13.97
        place(f'#FLG{i + 1:02d}', 'power:PWR_FLAG', 'PWR_FLAG', x, y, 0, bom=False)
        wire(x, y, x, y + 2.54)
        if net in POWER:
            power(net, x, y + 2.54, (0, 1))
        else:
            label(net, x, y + 2.54, (0, 1))

    text('Board A "knob-base" (GaggiMate knob rev 1). Circuit from SmartKnob View view_base (Scott Bezek, Apache-2.0):\n'
         'kept MT6701 encoder, HX711 + PNP AVDD regulator, 4x 2512 strain-gauge bridge, GNDA net tie.\n'
         'Removed: ESP32, USB/CH340, regulators, TMC6300, LEDs, VEML7700, LCD pads, J4/J5 gauge pads.\n'
         'Changes: L1 3.3uH -> FB1 basic ferrite bead; S8550-family PNP (C8542, basic) instead of MMBT4403;\n'
         'power + data from Board B on J1 (JST-SH 8p): 1 3V3, 2 GND, 3 ENC_CS, 4 ENC_CLK, 5 ENC_DO, 6 HX_SCK, 7 HX_DOUT, 8 GND.',
         20.32, 20.32, 1.5)
    text('Encoder (centre, front side)', 22.86, 43.18, 1.8)
    text('Press sensor ADC', 180.34, 33.02, 1.8)
    text('HX711 AVDD regulator, excitation filter, input filter, decoupling', 22.86, 111.76, 1.8)
    text('Strain-gauge bridge on the flexure (back side). E+ = filtered AVDD; S+/S- to INA+/INA-.', 22.86, 157.48, 1.8)
    s.append('(sheet_instances (path "/" (page "1")))')
    s.append('(embedded_fonts no))')
    OUT.write_text('\n'.join(s) + '\n')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
