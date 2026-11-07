"""Project-local footprints for knob-main (board B)."""
import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'knob-main.pretty')


def wirepads13():
    s = ['(footprint "WirePads_13_2Rows_P2.0mm" (version 20240108) (generator "knob-gen")',
         '  (layer "F.Cu")',
         '  (descr "13 THT solder pads for the 30AWG screen-wire bundle: row A pads 1-7 at y=0 (2.0 mm pitch), row B pads 8-13 at y=2.0, staggered by 1 mm. Drill 0.9 mm.")',
         '  (attr through_hole exclude_from_pos_files exclude_from_bom)',
         '  (property "Reference" "J7" (at 0 -1.9 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
         '  (property "Value" "ScreenWires" (at 0 4.0 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
         '  (fp_rect (start -7.0 -0.95) (end 7.0 2.95) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))',
         '  (fp_line (start -7.3 -1.0) (end -7.3 1.0) (stroke (width 0.15) (type solid)) (layer "F.SilkS"))']
    pads = [(i + 1, -6.0 + 2.0 * i, 0.0) for i in range(7)] + [(8 + i, -5.0 + 2.0 * i, 2.0) for i in range(6)]
    for n, x, y in pads:
        shape = 'rect' if n == 1 else 'circle'
        s.append('  (pad "%d" thru_hole %s (at %.3f %.3f) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))' % (n, shape, x, y))
    s.append(')')
    open(os.path.join(OUT, 'WirePads_13_2Rows_P2.0mm.kicad_mod'), 'w').write('\n'.join(s) + '\n')



def motorpads3():
    s = ['(footprint "MotorPads_3_P2.54mm" (version 20240108) (generator "knob-gen")',
         '  (layer "F.Cu")',
         '  (descr "3 bare THT solder pads (motor phases A/B/C) at 2.54 mm pitch, drill 1.0 mm. No part fitted.")',
         '  (attr through_hole exclude_from_pos_files exclude_from_bom)',
         '  (property "Reference" "J6" (at -2.0 0 90) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
         '  (property "Value" "MotorPads" (at 2.0 2.54 90) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
         '  (fp_rect (start -1.15 -1.15) (end 1.15 6.23) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))']
    for i, ph in enumerate('ABC'):
        shape = 'rect' if i == 0 else 'circle'
        s.append('  (pad "%d" thru_hole %s (at 0 %.2f) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))' % (i + 1, shape, 2.54 * i))
    s.append(')')
    open(os.path.join(OUT, 'MotorPads_3_P2.54mm.kicad_mod'), 'w').write('\n'.join(s) + '\n')


wirepads13()
motorpads3()


def symbols():
    """Project-local symbol library: AP7361C-33ER (SOT-223R pinout 1 GND, 2 VO/tab, 3 VI), not in KiCad's stock libs.
    Built from the stock AMS1117-3.3 symbol, which has the same pin numbering (checked against Diodes DS37274 Rev.5-2 p.2)."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from kgen_sch import flat
    from sexp import dump, find, Str
    s = flat('Regulator_Linear', 'AMS1117-3.3')
    old = s[1]
    s[1] = Str('AP7361C-33ER')
    for u in find(s, 'symbol'):
        u[1] = Str('AP7361C-33ER' + u[1][len(old):])
    newp = {'Value': 'AP7361C-33ER', 'Datasheet': 'https://www.diodes.com/assets/Datasheets/AP7361C.pdf',
            'Description': '1A low-dropout regulator (340 mV @ 1 A), fixed 3.3 V, SOT-223R (1 GND, 2 OUT/tab, 3 IN)',
            'ki_keywords': 'regulator linear ldo fixed positive', 'Footprint': 'Package_TO_SOT_SMD:SOT-223-3_TabPin2'}
    for p in find(s, 'property'):
        if p[1] in newp:
            p[2] = Str(newp[p[1]])
    lib = ['kicad_symbol_lib', ['version', 20231120], ['generator', Str('knob-gen')], s]
    open(os.path.join(os.path.dirname(OUT), 'knob-main.kicad_sym'), 'w').write(dump(lib) + '\n')


symbols()
