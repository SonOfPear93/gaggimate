"""Board C "knob-screen": generate the schematic + project file.
Run with any python3 (needs scripts dir with sexp.py/kgen_sch.py on sys.path, see ../../knob-main/gen)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'knob-main', 'gen'))
from kgen_sch import Comp, Sheet, write_pro, netclass

PRJ = 'knob-screen'
OUT = os.path.join(HERE, '..')

# 13-wire bundle, identical numbering on board B (J7) and board C (J2)
WIRES = ['3V3_LCD', 'GND', 'LCD_CS', 'LCD_CLK', 'LCD_D0', 'LCD_D1', 'LCD_D2', 'LCD_D3', 'LCD_RST',
         'TP_SDA', 'TP_SCL', 'TP_INT', 'TP_RST']

# Panel FPC pinout (Waveshare ESP32-S3-Touch-AMOLED-1.75 schematic, J3)
FPC = {}
for p in (1, 4, 7, 10, 20, 25, 31):
    FPC[p] = 'GND'
for p in (21, 22, 23, 24, 26):
    FPC[p] = '3V3_LCD'
FPC.update({11: 'LCD_TE', 12: 'LCD_D2', 13: 'LCD_D3', 14: 'LCD_CLK', 15: 'LCD_D1', 16: 'LCD_D0',
            17: 'LCD_CS', 18: 'LCD_RST', 27: 'TP_SCL', 28: 'TP_SDA', 29: 'TP_RST', 30: 'TP_INT'})

sh = Sheet(PRJ, 'GaggiMate Knob - board C (screen adapter)', paper='A3', comments=(
    'Adapter between the 1.75in CO5300/CST9217 AMOLED (31-pin 0.3 mm FPC) and the 13-wire bundle to board B',
    'FPC pinout copied from Waveshare ESP32-S3-Touch-AMOLED-1.75 schematic (J3). Panel makes its own AMOLED rails from 3V3.',
    'I2C pull-ups for touch live on board B (to 3V3_LCD). No active parts on this board.'))

pins = {str(k): v for k, v in FPC.items()}
pins['MP'] = 'GND'
sh.add(Comp('J1', 'Connector_Generic_MountingPin:Conn_01x31_MountingPin', 'FH26W-31S-0.3SHW(60)',
            'Connector_FFC-FPC:Hirose_FH26-31S-0.3SHW_2Rows-31Pins-1MP_P0.60mm_Horizontal', 'C2973806', pins,
            desc='Hirose FH26W 31P 0.3 mm bottom-contact back-flip FPC connector (panel tail)', mpn='FH26W-31S-0.3SHW(60)'), 'conn')
sh.add(Comp('J2', 'Connector_Generic:Conn_01x13', 'WirePads13', 'knob-screen:WirePads_Ring13_R5.5mm', '',
            {str(i + 1): n for i, n in enumerate(WIRES)}, in_bom=False,
            desc='13 solder pads (bottom side) for the wire bundle from board B J7, same numbering'), 'conn')
sh.add(Comp('TP1', 'Connector:TestPoint', 'LCD_TE', 'TestPoint:TestPoint_Pad_D1.0mm', '', {'1': 'LCD_TE'}, in_bom=False,
            desc='Panel tearing-effect output, pad only (not wired in rev 1)'), 'conn')
sh.add(Comp('C1', 'Device:C', '10uF', 'Capacitor_SMD:C_0603_1608Metric', 'C19702', {'1': '3V3_LCD', '2': 'GND'},
            mpn='CL10A106KP8NNNC'), 'pwr')
sh.add(Comp('C2', 'Device:C', '1uF', 'Capacitor_SMD:C_0402_1005Metric', 'C52923', {'1': '3V3_LCD', '2': 'GND'},
            mpn='CL05A105KA5NQNC'), 'pwr')
sh.add(Comp('C3', 'Device:C', '100nF', 'Capacitor_SMD:C_0402_1005Metric', 'C1525', {'1': '3V3_LCD', '2': 'GND'},
            mpn='CL05B104KO5NNNC'), 'pwr')
sh.add(Comp('C4', 'Device:C', '100nF', 'Capacitor_SMD:C_0402_1005Metric', 'C1525', {'1': '3V3_LCD', '2': 'GND'},
            mpn='CL05B104KO5NNNC'), 'pwr')
for i in range(3):
    sh.add(Comp('H%d' % (i + 1), 'Mechanical:MountingHole', 'M2', 'MountingHole:MountingHole_2.2mm_M2', '', {}, in_bom=False), 'mech')

sh.text('Notes:\n'
        '- J1 sits on the panel-facing (top) side, positioned like Waveshare\'s J3 so the panel FPC tail folds behind\n'
        '  the glass and reaches it. FPC enters from -X (board left). Max part height on top: 1.0 mm (FPC fold gap ~2.3 mm).\n'
        '- J2 is 13 bare SMD pads on the bottom side in a ring r=5.5 mm around the board centre (motor hollow shaft).\n'
        '- Panel 3V3 (3V3_LCD) is switched on board B (LCD_EN). Bulk/HF decoupling here, close to the FPC 3V3 pins.\n'
        '- LCD_TE is brought to a test pad only.', 25.4, 230, 1.8)

if '--pro-only' not in sys.argv:
    uc = sh.unconnected_report()
    print('No-connect pins:', ' '.join(uc))
    sh.write(os.path.join(OUT, PRJ + '.kicad_sch'), maxw=330)

rules = {"min_clearance": 0.15, "min_track_width": 0.15, "min_via_diameter": 0.5, "min_through_hole_diameter": 0.3,
         "min_via_annular_width": 0.1, "min_hole_clearance": 0.25, "min_hole_to_hole": 0.25,
         "min_copper_edge_clearance": 0.3, "min_silk_clearance": 0.0, "min_text_height": 0.6, "min_text_thickness": 0.08,
         "solder_mask_to_copper_clearance": 0.0, "max_error": 0.005, "min_resolved_spokes": 2, "min_connection": 0.0,
         "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1, "solder_mask_clearance": 0.0, "solder_mask_min_width": 0.0,
         "use_height_for_length_calcs": True}
write_pro(os.path.join(OUT, PRJ + '.kicad_pro'), PRJ,
          [netclass('Default', 0.15, 0.15, 0.5, 0.3), netclass('Power', 0.4, 0.15, 0.6, 0.3)],
          [{"netclass": "Power", "pattern": "/3V3_LCD"}, {"netclass": "Power", "pattern": "/GND"}], rules)
open(os.path.join(OUT, 'fp-lib-table'), 'w').write(
    '(fp_lib_table\n  (version 7)\n  (lib (name "knob-screen")(type "KiCad")(uri "${KIPRJMOD}/knob-screen.pretty")(options "")(descr "Board C local footprints"))\n)\n')
