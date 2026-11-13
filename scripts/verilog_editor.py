"""Editor de Verilog con resaltado de sintaxis dentro de un notebook de Colab.

El visor de archivos de Colab no reconoce la extensión .v, así que muestra el
código sin colores. Este módulo pone en la salida de la celda un editor
CodeMirror (modo Verilog, números de línea) con botón "Guardar" que escribe el
archivo en disco mediante un callback de Colab. También guarda con Ctrl+S
(Cmd+S en Mac) cuando el cursor está dentro del editor.

Fuera de Colab (Jupyter local, pruebas automáticas) muestra el código con
resaltado de solo lectura (pygments).

Uso:
    from verilog_editor import editor
    editor('/content/diseno/counter.v')
"""
import html
import json
import pathlib

CM = "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16"


def _solo_lectura(ruta):
    from IPython.display import HTML, display
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import VerilogLexer
    fmt = HtmlFormatter(noclasses=True, style="friendly", linenos="inline")
    display(HTML(f"<b>{html.escape(ruta.name)}</b>" + highlight(ruta.read_text(), VerilogLexer(), fmt)))


def editor(ruta, alto=360):
    from IPython.display import HTML, display
    ruta = pathlib.Path(ruta)
    try:
        from google.colab import output
    except ImportError:
        _solo_lectura(ruta)
        return
    uid = "ed_" + "".join(ch if ch.isalnum() else "_" for ch in ruta.name)

    def _guardar(texto):
        ruta.write_text(texto)
        return "ok"

    output.register_callback(f"guardar_{uid}", _guardar)
    contenido = json.dumps(ruta.read_text())
    display(HTML(f"""
<link rel="stylesheet" href="{CM}/codemirror.min.css">
<style>
  #{uid}_caja {{ border: 1px solid #bbb; border-radius: 4px; margin-bottom: 4px; }}
  #{uid}_caja .CodeMirror {{ font-size: 13px; }}
  #{uid}_barra {{ font-family: sans-serif; font-size: 13px; margin: 6px 0; }}
  #{uid}_barra button {{ margin-left: 10px; padding: 2px 12px; cursor: pointer; }}
</style>
<div id="{uid}_barra"><b>{html.escape(ruta.name)}</b>
  <button id="{uid}_btn">Guardar</button>
  <span id="{uid}_estado" style="margin-left:10px;color:#666">sin cambios</span></div>
<div id="{uid}_caja"><textarea id="{uid}_txt"></textarea></div>
<script>
(async () => {{
  const carga = (src) => new Promise((ok, mal) => {{
    const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = mal;
    document.head.appendChild(s);
  }});
  const estado = document.getElementById('{uid}_estado');
  try {{
    if (!window.CodeMirror) await carga('{CM}/codemirror.min.js');
    if (!CodeMirror.modes.verilog) await carga('{CM}/mode/verilog/verilog.min.js');
  }} catch (e) {{
    estado.textContent = 'no se pudo cargar el editor (sin internet en el navegador?)';
    return;
  }}
  const ed = CodeMirror.fromTextArea(document.getElementById('{uid}_txt'), {{
    mode: 'text/x-verilog', lineNumbers: true, indentUnit: 2, tabSize: 2,
    matchBrackets: true, viewportMargin: Infinity
  }});
  ed.setValue({contenido});
  ed.setSize(null, {int(alto)});
  const guardar = async () => {{
    estado.textContent = 'guardando...';
    try {{
      await google.colab.kernel.invokeFunction('guardar_{uid}', [ed.getValue()], {{}});
      estado.style.color = '#2a7'; estado.textContent = 'guardado ' + new Date().toLocaleTimeString();
    }} catch (e) {{
      estado.style.color = '#c33'; estado.textContent = 'error al guardar: ' + e;
    }}
  }};
  ed.setOption('extraKeys', {{ 'Ctrl-S': guardar, 'Cmd-S': guardar }});
  ed.on('change', () => {{ estado.style.color = '#c80'; estado.textContent = 'cambios sin guardar'; }});
  document.getElementById('{uid}_btn').onclick = guardar;
}})();
</script>
"""))
