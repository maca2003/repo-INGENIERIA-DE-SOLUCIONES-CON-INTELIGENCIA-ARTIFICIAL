"""Genera TODA la evidencia del proyecto con un solo comando.

Uso (desde la raíz del proyecto, con el entorno virtual activo):

    python src/generar_evidencias.py              # con el modelo real del .env
    python src/generar_evidencias.py --capturas   # + capturas de la interfaz
    python src/generar_evidencias.py --simulado   # sin LLM (solo para probar)
    python src/generar_evidencias.py --solo-observabilidad --capturas   # solo la EP3

Pasos que ejecuta y dónde deja cada resultado:

    1. probar_modelos.py         -> evidencias/ejecucion/01_probar_modelos.txt
    2. crear_base_vectorial.py   -> evidencias/ejecucion/02_base_vectorial.txt (si no existe)
    3. pytest -v (toda la suite) -> evidencias/pytest_output.txt
    4. pytest -m real -v         -> evidencias/pytest_real_output.txt
    5. demo_escenarios.py        -> evidencias/agente/<proveedor>/
    6. evaluar_rag.py (EP1)      -> evidencias/resultados_evaluacion.json
    --capturas: Streamlit + Playwright -> evidencias/capturas/<proveedor>/*.png
    7. evaluar_observabilidad.py -> evidencias/observabilidad/<proveedor>/ (métricas base vs optimizado)
    8. analizar_logs.py          -> evidencias/observabilidad/<proveedor>/hallazgos_logs.md
    --capturas: dashboard        -> evidencias/capturas/dashboard/<proveedor>/*.png

Al final escribe evidencias/RESUMEN_EVIDENCIAS.md con el estado de cada paso.
"""

import argparse
import unicodedata
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EVIDENCIAS = RAIZ / "evidencias"
EJECUCION = EVIDENCIAS / "ejecucion"
sys.path.insert(0, str(RAIZ / "src"))


def ejecutar(nombre: str, comando: list[str], salida: Path, timeout: int = 3600) -> dict:
    """Ejecuta un comando, muestra su salida y la guarda en un archivo."""
    print(f"\n=== {nombre} ===")
    print("$ " + " ".join(comando))
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    inicio = time.perf_counter()
    try:
        proceso = subprocess.run(comando, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8",
                                 errors="replace", timeout=timeout, env=entorno)
        texto, codigo = proceso.stdout + proceso.stderr, proceso.returncode
    except subprocess.TimeoutExpired:
        texto, codigo = f"Tiempo agotado ({timeout} s)", -1
    segundos = round(time.perf_counter() - inicio, 1)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(f"$ {' '.join(comando)}\n# {datetime.now():%Y-%m-%d %H:%M}\n\n{texto}", encoding="utf-8")
    ultimas = "\n".join(texto.strip().splitlines()[-6:])
    print(ultimas)
    estado = "OK" if codigo == 0 else f"ERROR ({codigo})"
    print(f"-> {estado} en {segundos} s · {salida.relative_to(RAIZ)}")
    return {"paso": nombre, "estado": estado, "segundos": segundos, "archivo": salida.relative_to(RAIZ).as_posix(),
            "resumen": ultimas.splitlines()[-1] if ultimas else ""}


def contar_base_vectorial() -> int:
    """Cantidad de fragmentos en la base de conocimiento del proveedor actual."""
    from langchain_chroma import Chroma

    from agente import config, modelos
    base = Chroma(collection_name=config.COLECCION_CONOCIMIENTO, embedding_function=modelos.crear_embeddings(),
                  persist_directory=str(modelos.carpeta_chroma(RAIZ)))
    return base._collection.count()


def esperar_servidor(url: str, segundos: int = 90) -> bool:
    limite = time.time() + segundos
    while time.time() < limite:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def capturar_pantallas(simulado: bool, proveedor: str) -> dict:
    """Abre la interfaz, ejecuta 4 escenas de la demo y guarda capturas."""
    print("\n=== Capturas de la interfaz (Streamlit + Playwright) ===")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Falta Playwright: pip install -r requirements-evidencias.txt y python -m playwright install chromium")
        return {"paso": "Capturas de la interfaz", "estado": "OMITIDO (falta Playwright)", "segundos": 0,
                "archivo": "-", "resumen": "Instalar requirements-evidencias.txt"}

    carpeta = EVIDENCIAS / "capturas" / proveedor
    carpeta.mkdir(parents=True, exist_ok=True)
    puerto = "8599"
    servidor = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "src/app_agente.py", "--server.headless", "true",
         "--server.port", puerto], cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    inicio = time.perf_counter()
    archivos = []
    try:
        if not esperar_servidor(f"http://localhost:{puerto}"):
            raise RuntimeError("Streamlit no respondió")
        with sync_playwright() as p:
            # PLAYWRIGHT_CHROMIUM permite usar un Chromium ya instalado (opcional).
            navegador = p.chromium.launch(executable_path=os.getenv("PLAYWRIGHT_CHROMIUM") or None)
            pagina = navegador.new_page(viewport={"width": 1500, "height": 1000})
            pagina.goto(f"http://localhost:{puerto}")
            pagina.wait_for_timeout(4000)
            if simulado:
                pagina.get_by_text("simulado", exact=True).click()
                pagina.wait_for_timeout(2000)
            pagina.get_by_role("button", name="Nuevo hilo").click()
            pagina.wait_for_timeout(2000)

            def escribir(texto: str, esperar: str, archivo: str) -> None:
                caja = pagina.get_by_placeholder("Escribe una instrucción o pregunta")
                caja.fill(texto)
                caja.press("Enter")
                pagina.get_by_text(esperar).last.wait_for(timeout=600_000)
                pagina.wait_for_timeout(2000)
                pagina.screenshot(path=str(carpeta / archivo), full_page=True)
                archivos.append(archivo)
                print(f"  captura: evidencias/capturas/{proveedor}/{archivo}")

            escribir("Revisa la OP1003", "Aprobación requerida", "01_op1003_aprobacion_humana.png")
            pagina.get_by_role("button", name="✅ Aprobar envío").click()
            pagina.get_by_text("Revisión OP1003").last.wait_for(timeout=600_000)
            pagina.wait_for_timeout(2000)
            pagina.screenshot(path=str(carpeta / "02_op1003_plan_y_estado.png"), full_page=True)
            archivos.append("02_op1003_plan_y_estado.png")
            pagina.get_by_role("tab", name="Decisiones").click()
            pagina.wait_for_timeout(1000)
            pagina.screenshot(path=str(carpeta / "03_op1003_decisiones.png"), full_page=True)
            archivos.append("03_op1003_decisiones.png")
            pagina.get_by_role("tab", name="Plan").click()
            escribir("Llegó la lista de empaque corregida de la OP1003, reprocésala", "Derivada a revisión",
                     "04_op1003_correccion_replanificacion.png")
            escribir("Revisa la OP1004", "Revisión OP1004", "05_op1004_critica_escalada.png")
            pagina.get_by_role("tab", name="Memoria").click()
            pagina.wait_for_timeout(1000)
            pagina.screenshot(path=str(carpeta / "06_op1004_memoria_largo_plazo.png"), full_page=True)
            archivos.append("06_op1004_memoria_largo_plazo.png")
            navegador.close()
        estado = "OK"
    except Exception as error:
        estado = "ERROR: " + str(error).strip().splitlines()[0][:150]
        print(estado)
    finally:
        servidor.terminate()
    return {"paso": "Capturas de la interfaz", "estado": estado, "segundos": round(time.perf_counter() - inicio, 1),
            "archivo": f"evidencias/capturas/{proveedor}/", "resumen": f"{len(archivos)} capturas"}


def capturar_dashboard(proveedor: str) -> dict:
    """Captura cada pestaña del dashboard de observabilidad (EP3)."""
    print("\n=== Capturas del dashboard de observabilidad ===")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"paso": "Capturas del dashboard", "estado": "OMITIDO (falta Playwright)", "segundos": 0,
                "archivo": "-", "resumen": "Instalar requirements-evidencias.txt"}
    carpeta = EVIDENCIAS / "capturas" / "dashboard" / proveedor
    carpeta.mkdir(parents=True, exist_ok=True)
    puerto = "8598"
    servidor = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "src/dashboard_observabilidad.py", "--server.headless", "true",
         "--server.port", puerto, "--browser.gatherUsageStats", "false"],
        cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    inicio = time.perf_counter()
    archivos = []
    try:
        if not esperar_servidor(f"http://localhost:{puerto}"):
            raise RuntimeError("Streamlit no respondió")
        with sync_playwright() as p:
            navegador = p.chromium.launch(executable_path=os.getenv("PLAYWRIGHT_CHROMIUM") or None)
            pagina = navegador.new_page(viewport={"width": 1500, "height": 1000})
            pagina.goto(f"http://localhost:{puerto}")
            pagina.get_by_role("tab").first.wait_for(timeout=60_000)
            pagina.get_by_text(f"Benchmark · {proveedor}").click()
            pagina.wait_for_timeout(4000)
            for i, pestaña in enumerate(pagina.get_by_role("tab").all(), start=1):
                nombre = pestaña.inner_text().strip()
                pestaña.click()
                pagina.wait_for_timeout(3000)
                limpio = unicodedata.normalize("NFKD", nombre.lower()).encode("ascii", "ignore").decode()
                archivo = f"{i:02d}_{limpio.replace(' ', '_')}.png"
                pagina.screenshot(path=str(carpeta / archivo), full_page=True)
                archivos.append(archivo)
                print(f"  captura: evidencias/capturas/dashboard/{proveedor}/{archivo}")
            navegador.close()
        estado = "OK"
    except Exception as error:
        estado = "ERROR: " + str(error).strip().splitlines()[0][:150]
        print(estado)
    finally:
        servidor.terminate()
    return {"paso": "Capturas del dashboard", "estado": estado, "segundos": round(time.perf_counter() - inicio, 1),
            "archivo": f"evidencias/capturas/dashboard/{proveedor}/", "resumen": f"{len(archivos)} capturas"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera la evidencia del proyecto")
    parser.add_argument("--simulado", action="store_true", help="sin LLM (no sirve como evidencia real)")
    parser.add_argument("--capturas", action="store_true", help="captura la interfaz con Playwright")
    parser.add_argument("--sin-rag", action="store_true", help="omite la evaluación RAG de la EP1 (más rápido)")
    parser.add_argument("--solo-observabilidad", action="store_true",
                        help="solo los pasos de la EP3: benchmark, análisis de registros y capturas del dashboard")
    args = parser.parse_args()
    py = sys.executable
    pasos = []

    if args.simulado:
        proveedor, descripcion = "simulado", "modelo y embeddings deterministas, sin LLM"
    else:
        from agente import modelos
        proveedor, descripcion = modelos.proveedor(), modelos.describir()
    print(f"Proveedor: {descripcion}")

    if not args.simulado:
        paso = ejecutar("1. Verificar modelos", [py, "src/probar_modelos.py"], EJECUCION / "01_probar_modelos.txt", 600)
        pasos.append(paso)
        if paso["estado"] != "OK":
            print("\nEl modelo no responde. Revisa el .env (Ollama iniciado o GOOGLE_API_KEY) y vuelve a ejecutar.")
            escribir_resumen(pasos, proveedor, descripcion)
            sys.exit(1)
        if contar_base_vectorial() == 0:
            pasos.append(ejecutar("2. Crear base vectorial", [py, "src/crear_base_vectorial.py"],
                                  EJECUCION / "02_base_vectorial.txt", 1800))

    if args.solo_observabilidad:
        observabilidad(args, py, proveedor, pasos)
        escribir_resumen(pasos, proveedor, descripcion, sufijo="_observabilidad")
        return

    pasos.append(ejecutar("3. Pruebas automatizadas (suite completa)", [py, "-m", "pytest", "-v"],
                          EVIDENCIAS / "pytest_output.txt", 1800))
    if not args.simulado:
        pasos.append(ejecutar("4. Pruebas con el modelo real", [py, "-m", "pytest", "-m", "real", "-v"],
                              EVIDENCIAS / "pytest_real_output.txt", 1800))
    demo = [py, "src/demo_escenarios.py"] + (["--simulado"] if args.simulado else [])
    pasos.append(ejecutar("5. Escenarios de decisión", demo, EJECUCION / f"05_escenarios_{proveedor}.txt", 3600))
    if not args.simulado and not args.sin_rag:
        pasos.append(ejecutar("6. Evaluación RAG (EP1)", [py, "src/evaluar_rag.py"], EJECUCION / "06_evaluacion_rag.txt", 3600))
    if args.capturas:
        pasos.append(capturar_pantallas(args.simulado, proveedor))
    observabilidad(args, py, proveedor, pasos)
    escribir_resumen(pasos, proveedor, descripcion)


def observabilidad(args, py: str, proveedor: str, pasos: list[dict]) -> None:
    """Pasos de la EP3: métricas base vs optimizado, análisis de registros y dashboard."""
    bench = [py, "src/evaluar_observabilidad.py"] + (["--simulado"] if args.simulado else [])
    pasos.append(ejecutar("7. Benchmark de observabilidad", bench, EJECUCION / f"07_observabilidad_{proveedor}.txt", 7200))
    pasos.append(ejecutar("8. Análisis de registros", [py, "src/analizar_logs.py", "--proveedor", proveedor],
                          EJECUCION / f"08_analisis_logs_{proveedor}.txt", 600))
    if args.capturas:
        pasos.append(capturar_dashboard(proveedor))


def escribir_resumen(pasos: list[dict], proveedor: str, descripcion: str, sufijo: str = "") -> None:
    lineas = [
        "# Resumen de evidencias", "",
        f"- Fecha: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Proveedor del modelo: **{proveedor}** ({descripcion})",
        f"- Python: {sys.version.split()[0]} · Sistema: {sys.platform}", "",
        "| Paso | Estado | Tiempo (s) | Archivo | Última línea |", "|---|---|---:|---|---|",
    ]
    for p in pasos:
        lineas.append(f"| {p['paso']} | {p['estado']} | {p['segundos']} | `{p['archivo']}` | "
                      f"{p['resumen'].replace('|', '/')} |")
    if proveedor == "simulado":
        lineas += ["", "> Ejecución en modo simulado: verifica la orquestación, pero NO es evidencia del LLM real."]
    destino = EVIDENCIAS / f"RESUMEN_EVIDENCIAS_{proveedor}{sufijo}.md"
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"\nResumen: {destino.relative_to(RAIZ)}")
    for p in pasos:
        print(f"  [{p['estado']}] {p['paso']}")


if __name__ == "__main__":
    main()
