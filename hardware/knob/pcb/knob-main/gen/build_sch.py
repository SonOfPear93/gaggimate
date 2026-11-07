"""Board B "knob-main": generate the schematic + project file (python3 build_sch.py [--pro-only])."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kgen_sch
from kgen_sch import Comp, Sheet, write_pro, netclass
kgen_sch.EXTRA_LIBS['knob-main'] = os.path.join(HERE, '..', 'knob-main.kicad_sym')

PRJ = 'knob-main'
OUT = os.path.join(HERE, '..')

R0402 = 'Resistor_SMD:R_0402_1005Metric'
C0402 = 'Capacitor_SMD:C_0402_1005Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
C1206 = 'Capacitor_SMD:C_1206_3216Metric'
TPFP = 'TestPoint:TestPoint_Pad_D1.5mm'

RES = {'10k': ('C25744', '0402WGF1002TCE'), '5.1k': ('C25905', '0402WGF5101TCE'), '100k': ('C25741', '0402WGF1003TCE'),
       '4.7k': ('C25900', '0402WGF4701TCE'), '47k': ('C25792', '0402WGF4702TCE'), '1k': ('C11702', '0402WGF1001TCE'),
       '33': ('C25105', '0402WGF330JTCE'), '2.2k': ('C25879', '0402WGF2201TCE')}
CAP = {'100nF': (C0402, 'C1525', 'CL05B104KO5NNNC'), '1uF': (C0402, 'C52923', 'CL05A105KA5NQNC'),
       '10uF': (C0603, 'C19702', 'CL10A106KP8NNNC'), '10uF/25V': (C0805, 'C15850', 'CL21A106KAYNNNE'),
       '22uF/25V': (C1206, 'C12891', 'CL31A226KAHNNNE'), '22uF': (C0805, 'C45783', 'CL21A226MAQNNNE'),
       '100nF/50V': (C0603, 'C14663', 'CC0603KRX7R9BB104')}

sh = Sheet(PRJ, 'GaggiMate Knob - board B (main: ESP32-S3, DRV8311H, power)', paper='A1', comments=(
    'ESP32-S3-WROOM-1-N16R8 + DRV8311H (hardware mode, 3x PWM) + USB-C/JST-XH 5 V diode-OR + AP7361C-33ER LDO',
    'GPIO map = docs/superpowers/specs/2026-11-07-smartknob-input-design.md section 5',
    'Panel 3V3 switched by P-FET (LCD_EN high = on, ~1 ms soft start). Touch I2C pull-ups to 3V3_LCD.'))

n = {'R': 0, 'C': 0}


def R(val, a, b, group, ref=None):
    n['R'] += 1
    lc, mpn = RES[val]
    return sh.add(Comp(ref or 'R%d' % n['R'], 'Device:R', val if val != '33' else '33R', R0402, lc, {'1': a, '2': b}, mpn=mpn), group)


def C(val, a, b, group):
    n['C'] += 1
    fp, lc, mpn = CAP[val]
    return sh.add(Comp('C%d' % n['C'], 'Device:C', val, fp, lc, {'1': a, '2': b}, mpn=mpn), group)


# ---------------- power input ----------------
g = 'power'
usb = {p: 'GND' for p in ('A1', 'A12', 'B1', 'B12', 'SH')}
usb.update({p: 'VBUS' for p in ('A4', 'A9', 'B4', 'B9')})
usb.update({'A5': 'CC1', 'B5': 'CC2', 'A6': 'USB_DP', 'B6': 'USB_DP', 'A7': 'USB_DN', 'B7': 'USB_DN'})
sh.add(Comp('J1', 'Connector:USB_C_Receptacle_USB2.0_16P', 'USB-C', 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',
            'C165948', usb, mpn='TYPE-C-31-M-12', desc='USB-C 16P receptacle (USB 2.0): flashing, logs, bench power'), g)
R('5.1k', 'CC1', 'GND', g)
R('5.1k', 'CC2', 'GND', g)
sh.add(Comp('U2', 'Power_Protection:USBLC6-2SC6', 'USBLC6-2SC6', 'Package_TO_SOT_SMD:SOT-23-6', 'C2687116',
            {'1': 'USB_DP', '6': 'USB_DP', '3': 'USB_DN', '4': 'USB_DN', '2': 'GND', '5': 'VBUS'}, mpn='USBLC6-2SC6'), g)
sh.add(Comp('J2', 'Connector_Generic:Conn_01x04', 'B4B-XH-A', 'Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical',
            'C144395', {'1': 'VIN_XH', '2': 'XH_2', '3': 'XH_3', '4': 'GND'}, mpn='B4B-XH-A(LF)(SN)',
            desc='GaggiMate controller display cable: 1=+5V 2=ctrl UART_TX0 3=ctrl UART_RX0 4=GND (only 5V/GND used)'), g)
sh.add(Comp('D1', 'Device:D_Schottky', 'SS34', 'Diode_SMD:D_SMA', 'C8678', {'1': '+5V', '2': 'VBUS'}, mpn='SS34'), g)
sh.add(Comp('D2', 'Device:D_Schottky', 'SS34', 'Diode_SMD:D_SMA', 'C8678', {'1': '+5V', '2': 'VIN_XH'}, mpn='SS34'), g)
C('22uF/25V', '+5V', 'GND', g)
# AP7361C-33ER: 340 mV dropout @ 1 A (AMS1117: ~1.1 V) -> 3V3 keeps regulating from the ~4.5 V left after the Schottkys.
# 'ER' = SOT-223R pinout (1 GND, 2 OUT = tab, 3 IN), same as the 1117; the 'E' version (C500795) is 1 IN, 2 GND, 3 OUT
# and had 0 stock at JLC/LCSC on 2026-11-07.  Caps per datasheet: CIN >= 1 uF, COUT >= 2.2 uF ceramic (fitted: 10 uF / 22 uF + 100 nF).
sh.add(Comp('U3', 'knob-main:AP7361C-33ER', 'AP7361C-33ER-13', 'Package_TO_SOT_SMD:SOT-223-3_TabPin2', 'C3743528',
            {'1': 'GND', '2': '+3V3', '3': '+5V'}, mpn='AP7361C-33ER-13'), g)
C('10uF/25V', '+5V', 'GND', g)
C('22uF', '+3V3', 'GND', g)
C('100nF', '+3V3', 'GND', g)

# ---------------- ESP32 ----------------
g = 'mcu'
esp = {'1': 'GND', '40': 'GND', '41': 'GND', '2': '+3V3', '3': 'EN', '27': 'BOOT',
       '39': 'DRV_SOA', '38': 'DRV_SOB', '15': 'DRV_nFAULT', '4': 'DRV_INHA', '5': 'DRV_INHB',
       '6': 'TP_SCL', '7': 'TP_SDA', '12': 'TP_RST', '17': 'TP_INT',
       '18': 'QSPI_CS', '19': 'QSPI_D0', '20': 'QSPI_CLK', '21': 'QSPI_D1', '22': 'QSPI_D2', '8': 'QSPI_D3',
       '9': 'LCD_RST', '10': 'LCD_EN', '11': 'DRV_INHC', '13': 'USB_DN', '14': 'USB_DP', '23': 'DRV_nSLEEP',
       '31': 'ENC_CS', '32': 'ENC_CLK', '33': 'ENC_DO', '34': 'HX_SCK', '35': 'HX_DOUT',
       '37': 'U0TXD', '36': 'U0RXD', '24': 'DRV_EN', '25': 'STATUS_LED'}
sh.add(Comp('U1', 'RF_Module:ESP32-S3-WROOM-1', 'ESP32-S3-WROOM-1-N16R8', 'knob-main:ESP32-S3-WROOM-1_EPvia0.3', 'C2913202', esp,
            mpn='ESP32-S3-WROOM-1-N16R8', desc='ESP32-S3 module, 16 MB QIO flash, 8 MB OPI PSRAM (GPIO35-37 used internally)'), g)
C('10uF', '+3V3', 'GND', g)
C('100nF', '+3V3', 'GND', g)
R('10k', '+3V3', 'EN', g)
C('1uF', 'EN', 'GND', g)
sh.add(Comp('SW1', 'Switch:SW_Push', 'RESET', 'Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A', 'C318884',
            {'1': 'EN', '2': 'GND'}, mpn='TS-1187A-B-A-B'), g)
R('10k', '+3V3', 'BOOT', g)
sh.add(Comp('SW2', 'Switch:SW_Push', 'BOOT', 'Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A', 'C318884',
            {'1': 'BOOT', '2': 'GND'}, mpn='TS-1187A-B-A-B'), g)
R('1k', 'STATUS_LED', 'LED_A', g)
sh.add(Comp('D3', 'Device:LED', 'RED', 'LED_SMD:LED_0603_1608Metric', 'C2286', {'1': 'GND', '2': 'LED_A'}, mpn='KT-0603R'), g)
for nm, net in (('TP1', '+5V'), ('TP2', '+3V3'), ('TP3', 'GND'), ('TP4', 'U0TXD'), ('TP5', 'U0RXD'), ('TP6', 'XH_2'), ('TP7', 'XH_3')):
    sh.add(Comp(nm, 'Connector:TestPoint', net.replace('+', ''), TPFP, '', {'1': net}, in_bom=False), g)

# ---------------- display / touch ----------------
g = 'lcd'
for sig in ('CS', 'CLK', 'D0', 'D1', 'D2', 'D3'):
    R('33', 'QSPI_' + sig, 'LCD_' + sig, g)
R('4.7k', 'TP_SCL', '3V3_LCD', g)
R('4.7k', 'TP_SDA', '3V3_LCD', g)
sh.add(Comp('Q1', 'Transistor_FET:AO3401A', 'AO3401A', 'Package_TO_SOT_SMD:SOT-23', 'C15127',
            {'1': 'LCD_PG', '2': '+3V3', '3': '3V3_LCD'}, mpn='AO3401A', desc='Panel 3V3 high-side switch'), g)
R('100k', 'LCD_PG', '+3V3', g)
C('100nF', 'LCD_PG', '+3V3', g)
R('10k', 'LCD_PG', 'LCD_PGD', g)
sh.add(Comp('Q2', 'Transistor_FET:2N7002', '2N7002', 'Package_TO_SOT_SMD:SOT-23', 'C8545',
            {'1': 'LCD_EN', '2': 'GND', '3': 'LCD_PGD'}, mpn='2N7002'), g)
R('100k', 'LCD_EN', 'GND', g)
C('10uF', '3V3_LCD', 'GND', g)
WIRES = ['3V3_LCD', 'GND', 'LCD_CS', 'LCD_CLK', 'LCD_D0', 'LCD_D1', 'LCD_D2', 'LCD_D3', 'LCD_RST',
         'TP_SDA', 'TP_SCL', 'TP_INT', 'TP_RST']
sh.add(Comp('J7', 'Connector_Generic:Conn_01x13', 'ScreenWires', 'knob-main:WirePads_13_2Rows_P2.0mm', '',
            {str(i + 1): w for i, w in enumerate(WIRES)}, in_bom=False,
            desc='13 solder pads for the wire bundle to board C J2 (same numbering)'), g)

# ---------------- motor driver ----------------
g = 'motor'
drv = {'1': 'DRV_nFAULT', '2': 'DRV_AVDD', '4': 'DRV_SOB', '5': 'DRV_SOA', '6': 'DRV_CP', '7': '+5V', '8': '+5V',
       '9': 'GND', '25': 'GND', '16': 'GND', '10': 'MOT_A', '11': 'MOT_B', '12': 'MOT_C',
       '15': 'DRV_INHA', '14': 'DRV_INHB', '13': 'DRV_INHC', '18': 'DRV_EN', '19': 'DRV_EN', '20': 'DRV_EN',
       '17': 'DRV_AVDD', '22': 'DRV_SLEW', '23': 'DRV_AVDD', '24': 'DRV_nSLEEP'}
# pin 3 SOC unused, pin 21 GAIN left open (Hi-Z = 1 V/A)
sh.add(Comp('U4', 'Driver_Motor:DRV8311H', 'DRV8311HRRWR',
            'Package_DFN_QFN:Texas_RRW0024A_WQFN-24-1EP_3x3mm_P0.4mm_EP1.9x1.9mm', 'C5218862', drv,
            mpn='DRV8311HRRWR', desc='3-phase driver, MODE=AVDD (3x PWM, OCP 5 A), GAIN open (1 V/A), SLEW 47k->GND (75 V/us)'), g)
R('10k', 'DRV_nFAULT', '+3V3', g)
R('100k', 'DRV_nSLEEP', 'GND', g)
R('100k', 'DRV_EN', 'GND', g)
R('47k', 'DRV_SLEW', 'GND', g)
C('100nF', 'DRV_AVDD', 'GND', g)        # CSAREF
C('1uF', 'DRV_AVDD', 'GND', g)          # AVDD
C('100nF/50V', 'DRV_CP', '+5V', g)      # CP-VM
C('100nF/50V', '+5V', 'GND', g)         # VM HF
C('22uF/25V', '+5V', 'GND', g)          # VM bulk
C('22uF/25V', '+5V', 'GND', g)          # VM bulk
C('100nF', '+5V', 'GND', g)             # VIN_AVDD
C('10uF/25V', '+5V', 'GND', g)          # VIN_AVDD bulk
sh.add(Comp('J5', 'Connector_Generic_MountingPin:Conn_01x03_MountingPin', '53261-0371',
            'Connector_Molex:Molex_PicoBlade_53261-0371_1x03-1MP_P1.25mm_Horizontal', 'C293630',
            {'1': 'MOT_A', '2': 'MOT_B', '3': 'MOT_C'}, mpn='532610371', desc='Motor phases (Molex PicoBlade, as SmartKnob)'), g)
sh.add(Comp('J6', 'Connector_Generic:Conn_01x03', 'MotorPads', 'knob-main:MotorPads_3_P2.54mm', '',
            {'1': 'MOT_A', '2': 'MOT_B', '3': 'MOT_C'}, in_bom=False, desc='Motor phase solder pads (alternative to J5)'), g)

# ---------------- board A link ----------------
g = 'link'
sh.add(Comp('J8', 'Connector_Generic_MountingPin:Conn_01x08_MountingPin', 'SM08B-SRSS-TB',
            'Connector_JST:JST_SH_SM08B-SRSS-TB_1x08-1MP_P1.00mm_Horizontal', 'C160407',
            {'1': '+3V3', '2': 'GND', '3': 'ENC_CS', '4': 'ENC_CLK', '5': 'ENC_DO', '6': 'HX_SCK', '7': 'HX_DOUT', '8': 'GND'},
            mpn='SM08B-SRSS-TB(LF)(SN)', desc='To board A (knob-base): MT6701 SSI + HX711'), g)
for sig in ('ENC_CS', 'ENC_CLK', 'ENC_DO'):     # board A has none; SmartKnob used 2.2k on the MT6701 SSI lines
    R('2.2k', sig, '+3V3', g)
for i in range(4):
    sh.add(Comp('H%d' % (i + 1), 'Mechanical:MountingHole', 'M2', 'MountingHole:MountingHole_2.2mm_M2', '', {}, in_bom=False), 'mech')

sh.flags = ['GND', '+5V', 'VBUS', 'VIN_XH']

sh.text('Design notes (board B):\n'
        '- Power: USB-C VBUS and the GaggiMate cable (J2 pin1 +5V, pin4 GND, same pinout as the controller J4 display\n'
        '  connector) are OR-ed by two SS34 Schottkys into +5V (~4.6 V). +5V feeds DRV8311H VM/VIN_AVDD and the AP7361C-33ER LDO.\n'
        '- DRV8311H hardware variant: MODE tied to AVDD = 3x PWM mode (OCP 5 A). INHx = PWM from ESP32, all INLx tied to\n'
        '  DRV_EN (GPIO47, 100k pull-down -> outputs Hi-Z at boot). nSLEEP GPIO21 with 100k pull-down. GAIN pin open = Hi-Z\n'
        '  = 1 V/A CSA gain (+/-1.65 A range). SLEW 47k to GND = 75 V/us (dead time per datasheet). SOA/SOB -> GPIO1/GPIO2 (ADC1).\n'
        '- Panel QSPI lines have 33R series resistors at the ESP32 (wire bundle ~10-15 cm long).\n'
        '- Panel 3V3 (3V3_LCD) via AO3401A; firmware should keep LCD/TP pins low or Hi-Z while LCD_EN is low.\n'
        '- MT6701 SSI lines (ENC_CS/CLK/DO) have 2.2k pull-ups here (board A has none), as SmartKnob.\n'
        '- J7 (13 pads) and J6 (motor pads) are bare pads, not populated. Test pads TP1-TP7 are bare pads.',
        25.4, 520, 2.0)

if '--pro-only' not in sys.argv:
    print('No-connect pins:', ' '.join(sh.unconnected_report()))
    sh.write(os.path.join(OUT, PRJ + '.kicad_sch'), maxw=780)

rules = {"min_clearance": 0.127, "min_track_width": 0.127, "min_via_diameter": 0.5, "min_through_hole_diameter": 0.3,
         "min_via_annular_width": 0.1, "min_hole_clearance": 0.25, "min_hole_to_hole": 0.25,
         "min_copper_edge_clearance": 0.3, "min_silk_clearance": 0.0, "min_text_height": 0.6, "min_text_thickness": 0.08,
         "solder_mask_to_copper_clearance": 0.0, "max_error": 0.005, "min_resolved_spokes": 2, "min_connection": 0.0,
         "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1, "solder_mask_clearance": 0.0, "solder_mask_min_width": 0.0,
         "use_height_for_length_calcs": True}
write_pro(os.path.join(OUT, PRJ + '.kicad_pro'), PRJ,
          [netclass('Default', 0.2, 0.15, 0.6, 0.3), netclass('Power', 0.5, 0.2, 0.8, 0.4),
           netclass('PowerIn', 0.4, 0.2, 0.8, 0.4), netclass('Motor', 0.5, 0.2, 0.8, 0.4), netclass('USB', 0.3, 0.15, 0.6, 0.3), netclass('Plane', 0.4, 0.2, 0.6, 0.3)],
          [{"netclass": "Power", "pattern": "/+5V"}, {"netclass": "PowerIn", "pattern": "/VBUS"},
           {"netclass": "PowerIn", "pattern": "/VIN_XH"}, {"netclass": "PowerIn", "pattern": "/3V3_LCD"},
           {"netclass": "Motor", "pattern": "/MOT_*"}, {"netclass": "USB", "pattern": "/USB_D*"},
           {"netclass": "Plane", "pattern": "/GND"}, {"netclass": "Plane", "pattern": "/+3V3"}], rules)
