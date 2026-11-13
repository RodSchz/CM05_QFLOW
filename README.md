# CM05_QFLOW

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/RodSchz/CM05_QFLOW/blob/main/notebooks/CM05_QFLOW.ipynb)
[![Prueba del flujo](https://github.com/RodSchz/CM05_QFLOW/actions/workflows/test.yml/badge.svg)](https://github.com/RodSchz/CM05_QFLOW/actions/workflows/test.yml)

Flujo digital **Verilog → GDS** para el proceso **CIDESI_CM05** (CMOS, λ = 2.5 µm, 2 metales,
1 polisilicio) con [qflow](http://opencircuitdesign.com/qflow/), listo para usarse en Google Colab.

```
Verilog ──yosys──► netlist ──graywolf──► colocación ──qrouter (2 metales)──► ruteo
        ──magic/netgen──► LVS ──legalizador──► GDS ──KLayout + deck CIDESI_CM05──► DRC
```

## Uso rápido

Abre el notebook con el botón **Open in Colab** y ejecuta todas las celdas: instala las
herramientas, toma un ejemplo (o tu propio Verilog), corre el flujo completo y muestra el layout.

En una máquina con Ubuntu 22.04 o 24.04:

```bash
git clone https://github.com/RodSchz/CM05_QFLOW
git clone https://github.com/RodSchz/CIDESI_CM05          # deck DRC oficial
sudo bash CM05_QFLOW/scripts/install_tools.sh
export PATH=/opt/cm05_eda/bin:/opt/cm05_eda/shims:$PATH

mkdir -p trabajo/counter/source && cp CM05_QFLOW/examples/counter/counter.v trabajo/counter/source/
bash CM05_QFLOW/scripts/cm05_flow.sh counter trabajo/counter \
     CIDESI_CM05/tech/CIDESI_CM05/drc/drc.lydrc
# resultado: trabajo/counter/counter_cm05.gds y su reporte DRC (counter_cm05_drc.lyrdb)
```

## Biblioteca de celdas `cm05`

Derivada de la biblioteca OSU de qflow (`osu050`, AMI C5, reglas SCMOS SUBM): las reglas de diseño de
CIDESI_CM05 son el mismo juego SCMOS SUBM con λ = 2.5 µm, así que las celdas se escalan ×25/3.
Para adaptarlas a un proceso **de 2 metales y sin planarización**:

- Se quitó metal3/via2 y se rutea en 2 capas.
- **Regla 8.5** (Via1 a ≥ 2λ de bordes de poly/activo): se reubicaron las vías internas de
  DFFPOSX1 y cada pin quedó en un punto de la rejilla de ruteo donde una vía es legal; varias
  celdas se ensancharon uno o dos sitios (20 µm) para lograrlo.
- Se marcan con obstrucciones de M1 los puntos sobre las celdas donde una vía de ruteo sería ilegal.
- Cada celda modificada se verifica contra el deck oficial (0 errores), con equivalencia de netlist
  y W/L idénticos respecto a la original, y en abutamiento con todas las demás.

**Celdas disponibles:** INVX1/2/4/8, BUFX2/4, CLKBUF1/2/3, NAND2X1, NAND3X1, NOR2X1, NOR3X1,
AND2X1/2, OR2X1/2, AOI21X1, AOI22X1, OAI21X1, OAI22X1, MUX2X1, TBUFX1/2, DFFPOSX1.

**Limitaciones:**
- Solo **reset síncrono**: DFFSR (set/reset asíncrono), DFFNEGX1, LATCH, XOR2X1, XNOR2X1, FAX1 y
  HAX1 violan la regla 8.5 y están excluidas de la síntesis.
- El **liberty es aproximado**: tiempos y capacitancias de AMI C5 (0.5 µm). Sirve para mapear la
  lógica, no para estimar el desempeño en CM05.
- Con 2 metales el ruteo necesita espacio: el flujo reintenta con densidades de colocación de
  0.7 a 0.3, así que el área es mayor que en un proceso de 3 metales.

## Estructura

| Ruta | Contenido |
|---|---|
| `notebooks/CM05_QFLOW.ipynb` | Notebook de Colab (se genera con `tools/make_notebook.py`) |
| `tech/cm05/` | Tecnología qflow: LEF, GDS, SPICE y liberty de celdas, tech de magic, `.par`, `.sh` |
| `examples/` | Diseños de ejemplo: `counter`, `lfsr8`, `alu4`, `pwm8` |
| `scripts/cm05_flow.sh` | Flujo completo: qflow → GDS → legalizador → equivalencia → DRC |
| `scripts/install_tools.sh` | Instalación de herramientas (usa binarios del release si existen) |
| `scripts/build_cm05_tech.sh` | Reconstruye `tech/cm05` desde `osu050` con todas las correcciones |
| `docs/NOTAS_TECNICAS.md` | Decisiones y hallazgos de la adaptación |
| `.github/workflows/` | Binarios precompilados (release) y prueba del flujo en Ubuntu 22.04/24.04 |

Para reconstruir la biblioteca desde la tecnología `osu050` de qflow y verificarla:

```bash
DECK=CIDESI_CM05/tech/CIDESI_CM05/drc/drc.lydrc \
  bash scripts/build_cm05_tech.sh /opt/cm05_eda/share/qflow/tech/osu050
```

## Autor

Dr. Rodolfo Sánchez Fraga — Coordinación de Circuitos Integrados, CIDESI.

Licencia por definir. La biblioteca de celdas deriva de la biblioteca OSU distribuida con qflow;
el deck DRC pertenece al PDK [CIDESI_CM05](https://github.com/RodSchz/CIDESI_CM05).
