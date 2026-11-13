"""Renderiza un GDS a PNG con KLayout (sin GUI). Uso: gds2png.py in.gds out.png [ancho alto] [lyp]"""
import sys, klayout.lay as lay
w = int(sys.argv[3]) if len(sys.argv) > 3 else 1400
h = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
lv = lay.LayoutView()
lv.load_layout(sys.argv[1], True)
if len(sys.argv) > 5:
    lv.load_layer_props(sys.argv[5])
lv.max_hier(); lv.zoom_fit()
lv.set_config("background-color", "#ffffff")
lv.set_config("grid-visible", "true")
lv.save_image(sys.argv[2], w, h)
