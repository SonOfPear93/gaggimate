"""Generate project-local footprints for knob-screen (board C)."""
import math, os
OUT = os.path.join(os.path.dirname(__file__), '..', 'knob-screen.pretty')

def ring13(r=5.5, n=13, w=1.0, l=1.8):
    s = ['(footprint "WirePads_Ring13_R5.5mm" (version 20240108) (generator "knob-gen")',
         '  (layer "F.Cu")',
         '  (descr "13 SMD solder pads for 30AWG wires, radial ring r=5.5 mm around the board centre (wire bundle comes up the motor hollow shaft). Pad 1 at 90 deg (towards -Y), numbering clockwise as seen from this side.")',
         '  (attr smd exclude_from_pos_files exclude_from_bom)',
         '  (property "Reference" "J2" (at 0 -8.6 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
         '  (property "Value" "WirePads13" (at 0 8.8 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
         '  (fp_circle (center 0 0) (end 2.95 0) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
         '  (fp_circle (center 0 0) (end 7.0 0) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))',
         '  (fp_text user "SHAFT" (at 0 0 0) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.1))))']
    for i in range(n):
        a = -90 + i * 360.0 / n          # screen angle, y down: -90 = up
        x = r * math.cos(math.radians(a)); y = r * math.sin(math.radians(a))
        rot = -(a)                       # KiCad pad rotation is CCW-positive in screen coords
        s.append('  (pad "%d" smd roundrect (at %.4f %.4f %.3f) (size %.2f %.2f) (layers "F.Cu" "F.Mask") (roundrect_rratio 0.25))'
                 % (i + 1, x, y, rot, l, w))
        tx = (r + 1.75) * math.cos(math.radians(a)); ty = (r + 1.75) * math.sin(math.radians(a))
        s.append('  (fp_text user "%d" (at %.3f %.3f 0) (layer "F.SilkS") (effects (font (size 0.7 0.7) (thickness 0.12))))' % (i + 1, tx, ty))
    s.append(')')
    open(os.path.join(OUT, 'WirePads_Ring13_R5.5mm.kicad_mod'), 'w').write('\n'.join(s) + '\n')

ring13()
