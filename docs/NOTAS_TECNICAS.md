# Notas técnicas de la adaptación osu050 → cm05

## Reglas
- El deck de CIDESI_CM05 es MOSIS SCMOS opción SUBM con `LAMBDA = 2.5` y 2 metales: el mismo juego de
  reglas de las celdas OSU (SCN3ME_SUBM, λ = 0.3 µm). Escalar ×25/3 deja todos los vértices en la rejilla
  de ½λ = 1.25 µm.
- Pozo n sobre sustrato p, como OSU. Números de capa GDS MOSIS (42 Nwell … 51 Metal2), iguales a osu050.
- CM05 no tiene planarización: la regla 8.5 (Via1 a ≥ 2λ de bordes de poly/activo) y la 8.4 (Via1 fuera y
  a ≥ 2λ de contactos) aplican. AMI C5 sí permitía la vía sobre poly/activo, por eso las celdas OSU no cumplen.

## Tecnología de magic (`CM05.tech`)
- En `cifoutput`/`cifinput` las distancias de `squares`, `grow` y `bloat` están en centimicras absolutas,
  no en λ: además de `scalefactor` hay que escalarlas, o vías y contactos salen de 0.6 µm.
- `extract` declara `lambda` en centimicras: 30 → 250, o el W/L extraído para LVS queda en escala AMI.
- Se eliminan de la salida GDS las capas auxiliares de magic que chocan con el mapa de CM05
  (100/0 = Die.outline; 70–73 = ResBody/CapBody) o que no existen (61/62, 81–83, 109…).

## Celdas
- **DFFPOSX1**: vías internas reubicadas y celda ensanchada (240 → 280 µm) con cortes verticales que no
  cruzan compuertas (`fix_cell_vias.py`).
- **Acceso a pines** (`legalize_pins.py`): cada pin de señal en un punto de la rejilla de ruteo
  (x = 10 + 20i, y = 12.5 + 25j µm) donde una vía es legal; si no existe, se extiende M1 o se ensancha la
  celda un sitio. El OBS de metal1 deja libre el espaciado mínimo (7.5 µm) alrededor de cada pin, como el
  LEF original de OSU; sin ese hueco qrouter desplaza la vía fuera de pista.
- **Vías a mitad de ruta** (`add_via_block_obs.py`): cuadros de OBS de M1 de 1.25 µm en los puntos de
  rejilla donde una vía sería ilegal. No tocan metal, así que no unen redes en la vista abstracta de magic.
- Verificación por celda (`verify_cells.sh`): deck = 0, netlist equivalente, W/L idénticos.
  Abutamiento (`abut_test.py`): todas las celdas pegadas en N, espejo, alternado y filas FS = 0 errores.

## Ruteo y flujo
- Las celdas OSU con 2 capas no rutean sin estos cambios (osu050 original con `route_layers = 2` deja
  redes sin rutear).
- Franjas de alimentación de 20 µm: más anchas tapan los puertos de E/S de los bordes.
- **No usar `rowSep` > 0** en el `.par`: graywolf/qflow enciman filas y el LVS falla con cortos masivos.
  La palanca de ruteo es la densidad de colocación (`cm05_flow.sh` reintenta 0.7 → 0.5 → 0.4 → 0.3).
- `qflow gdsii` se niega a correr si el DRC de magic (sobre vistas abstractas LEF) reporta errores; el GDS
  se genera con `cm05_gds.sh` y el DRC de referencia es el deck de KLayout.
- `fix_route_vias.py` reubica las pocas vías de ruteo que aún violan 8.5 y `netcompare.py` confirma que el
  netlist extraído no cambia.

## Configuración de colocación
- Proporción del chip: `TWMC*chip.aspect.ratio` en el `.par` del proyecto (alto/ancho; el resultado es
  aproximado porque el alto se cuantiza en filas de 250 µm).
- Pines: `<modulo>.cel2` con un `padgroup` por lado (`restrict side L/R/T/B`). Con restricciones de lado
  graywolf amontona los pines (a 5 µm), así que `spread_pins.py` los reparte sobre pistas a lo largo del lado
  en el DEF colocado, entre `qflow place` y `qflow route`. `sidespace` no sirvió para repartirlos.
- Con 2 metales, los pines a izquierda/derecha (metal1) compiten con las franjas de alimentación vertical de
  los costados: lfsr8 con 8 salidas a la derecha no rutea ni a densidad 0.3; arriba/abajo (metal2) sí.

## Etiquetas de pines
- magic escribe las etiquetas de los puertos en las capas de dibujo (49/0, 51/0), con 0.3 µm de alto y rotadas.
  `pin_labels.py` las pasa a las capas de texto del PDK (49/1 Metal1.text, 51/1 Metal2.text, las que lee el LVS
  de CIDESI_CM05), horizontales y con alto configurable (`CM05_TEXTO`, 20 µm por omisión).
- KLayout dibuja los textos con una fuente de mapa de bits de tamaño fijo; para verlos a su tamaño real:
  File → Setup → Display → Texts → Font: Stick Font (en scripts: `text-font = 1`).

## Simulación
- `cm05_stdcells.v` sale de `osu05_stdcells.v` quitando solo los módulos de celdas excluidas y pads; las
  primitivas (`udp_dff`, `udp_mux2`, …) se conservan. Los retardos de `specify` son de AMI C5, así que la
  simulación post-layout se usa funcional (sin `-gspecify`).
- El netlist post-ruteo de qflow (`DEF2Verilog`) vuelve a declarar como `wire` los puertos ANSI; iverilog no
  lo acepta, así que `cm05_sim.sh` quita esas redeclaraciones antes de compilar.
- Prueba negativa: cambiar una NAND2X1 por NOR2X1 en el netlist post-ruteo hace fallar el testbench y la
  comparación de trazas.

## Intentos descartados
- Obstrucciones grandes en la capa `via` del LEF: qrouter las ignora y magic las toma como contactos M1–M2
  en la vista abstracta, cortocircuitando los pines en LVS.

## Herramientas
- Probado en Ubuntu 22.04 (Colab: yosys 0.9, magic 8.3.105, qrouter 1.4.71) y 24.04 (yosys 0.33).
- El DRC necesita KLayout ≥ 0.28; Ubuntu 22.04 trae 0.26 por apt, por eso el instalador usa el `.deb` oficial.
