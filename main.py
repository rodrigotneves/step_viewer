import sys
import os
import re
import ctypes
import numpy as np
from pathlib import Path

os.environ["QT_API"] = "pyside6"

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
    QHBoxLayout,
    QTextEdit,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)

from PySide6.QtGui import QIcon

if getattr(sys, "frozen", False):
    base = Path(sys.executable).parent / "_internal"
    sys.path.insert(0, str(base))
    os.environ["PATH"] = str(base) + os.pathsep + os.environ.get("PATH", "")

from cadquery import importers
import pyvista as pv
from pyvistaqt import QtInteractor
import vtk

vtk.vtkObject.GlobalWarningDisplayOff()

WINDOW_TITLE = "Visualizador de STEP"  # Título da janela, usado para o atalho e identificação do aplicativo no Windows.
APP_TITLE = "Visualizador de STEP"  # Título interno do aplicativo, para identificação no windows
DOMINIMO = "empresa"  # Ajuste para o appid do aplicativo, garantindo que o atalho e ícone funcionem corretamente no Windows.
VERSION = "V1"
BASE_PATH = Path(r"caminho\para\pasta") # Pasta base onde o programa irá procurar os arquivos STEP, ajustável conforme a estrutura de pastas da empresa.


def get_resource_path(relative_path):
    """Garante que o PySide6 ache o arquivo tanto em dev quanto compilado"""
    if getattr(sys, "frozen", False):
        # No PyInstaller 6+ (modo pasta), os arquivos vão para a _internal
        base_path = Path(sys.executable).parent / "_internal"
    else:
        # Rodando normalmente pelo Python
        base_path = Path(__file__).parent

    return str(base_path / relative_path)



# regex separados
PG_REGEX = re.compile(r"(PG\d{4})[-_]?(\d{3})[-_]?(\d{2})", re.I)
CLIENT_REGEX = re.compile(r"([A-Z]{3}\d{3})[-_]?(\d{4})[-_]?(\d{3})[-_]?(\d{2})", re.I)


def step_to_pyvista_mesh(step_path, tolerance=0.05, angular_tolerance=0.2):

    shape = importers.importStep(str(step_path))

    vertices = []
    faces = []

    for solid in shape.solids():
        verts, tris = solid.tessellate(tolerance, angular_tolerance)

        v = [[p.x, p.y, p.z] for p in verts]

        offset = len(vertices)

        vertices.extend(v)

        for tri in tris:
            faces.append([3, tri[0] + offset, tri[1] + offset, tri[2] + offset])

    vertices = np.array(vertices)
    faces = np.hstack(faces)

    return pv.PolyData(vertices, faces)


class CadViewer(QMainWindow):
    def __init__(self):

        super().__init__()

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1400, 800)

        self.current_file_path = None
        self.found = {}

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)

        side_layout = QVBoxLayout()

        side_layout.addWidget(QLabel("Cole aqui os códigos dos desenhos"))

        self.codes_box = QTextEdit()
        self.codes_box.setMinimumWidth(350)
        side_layout.addWidget(self.codes_box)

        self.btn_resolve = QPushButton("Localizar STEP")
        self.btn_resolve.clicked.connect(self.resolve_codes)
        side_layout.addWidget(self.btn_resolve)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Código", "Status", "Caminho"])
        self.results_table.cellClicked.connect(self.table_clicked)

        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setWordWrap(False)
        self.results_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        side_layout.addWidget(self.results_table)

        self.btn_batch_print = QPushButton("Salvar prints na rede")
        self.btn_batch_print.clicked.connect(self.batch_print)
        side_layout.addWidget(self.btn_batch_print)
        self.btn_copy_missing = QPushButton("Copiar arquivos não encontrados")
        self.btn_copy_missing.clicked.connect(self.copy_missing)
        side_layout.addWidget(self.btn_copy_missing)

        side_layout.addStretch()

        self.btn_load = QPushButton("Abrir arquivo manualmente")
        self.btn_load.clicked.connect(self.load_step)
        side_layout.addWidget(self.btn_load)

        self.btn_print = QPushButton("Salvar peça atual em outro local")
        self.btn_print.clicked.connect(self.take_screenshot)
        self.btn_print.setEnabled(False)
        side_layout.addWidget(self.btn_print)

        main_layout.addLayout(side_layout)

        self.plotter = QtInteractor(self)
        main_layout.addWidget(self.plotter.interactor)

    # -----------------------------
    # PARSE
    # -----------------------------

    def parse_codes(self):

        raw = self.codes_box.toPlainText()

        tokens = re.split(r"[,\n; ]+", raw)

        codes = []

        for t in tokens:
            m_pg = PG_REGEX.search(t)
            m_client = CLIENT_REGEX.search(t)

            if m_pg:
                codes.append("-".join(m_pg.groups()).upper())

            elif m_client:
                codes.append("-".join(m_client.groups()).upper())

        return list(dict.fromkeys(codes))

    # -----------------------------
    # BUSCA CLIENTES
    # -----------------------------

    def find_client_step(self, code):

        m = CLIENT_REGEX.match(code)

        if not m:
            return None, None

        client, d1, d2, rev = m.groups()

        root = BASE_PATH / "CLIENTES"

        client_dir = root / client

        if not client_dir.exists():
            return None, client_dir

        best = None

        # procura até 3 níveis abaixo do cliente
        for path in client_dir.rglob(code):
            if path.is_dir():
                best = path

                step1 = path / f"{code}.stp"
                step2 = path / "stp" / f"{code}.stp"

                if step1.exists():
                    return step1, path

                if step2.exists():
                    return step2, path

        return None, best

    # -----------------------------
    # BUSCA PGS
    # -----------------------------

    def find_pg_step(self, code):

        m = PG_REGEX.match(code)

        if not m:
            return None, None

        client, d1, rev = m.groups()

        root = BASE_PATH / "PRODUTOS" / "PGS"

        client_dir = root / client

        if not client_dir.exists():
            return None, client_dir

        candidates = [
            client_dir / code,
            client_dir / f"{client}-{d1}" / code,
            client_dir / f"{client}-{d1}" / f"{client}-{d1}-{rev}" / code,
        ]

        best = None

        for c in candidates:
            if c.exists():
                best = c

                step1 = c / f"{code}.stp"
                step2 = c / "stp" / f"{code}.stp"

                if step1.exists():
                    return step1, c

                if step2.exists():
                    return step2, c

        return None, best

    # -----------------------------
    # RESOLVE
    # -----------------------------

    def resolve_codes(self):

        self.results_table.setRowCount(0)

        self.found = {}

        codes = self.parse_codes()

        for code in codes:
            if code.startswith("PG"):
                path, best = self.find_pg_step(code)
            else:
                path, best = self.find_client_step(code)

            row = self.results_table.rowCount()
            self.results_table.insertRow(row)

            code_item = QTableWidgetItem(code)
            code_item.setForeground(self.palette().link())

            self.results_table.setItem(row, 0, code_item)

            if path:
                self.found[code] = path

                self.results_table.setItem(
                    row, 1, QTableWidgetItem("✔ STEP encontrado")
                )

                self.results_table.setItem(row, 2, QTableWidgetItem(str(path)))

            elif best:
                self.results_table.setItem(
                    row, 1, QTableWidgetItem("⚠ STEP não encontrado")
                )

                self.results_table.setItem(row, 2, QTableWidgetItem(str(best)))

            else:
                base = BASE_PATH

                self.results_table.setItem(
                    row, 1, QTableWidgetItem("✖ STEP não encontrado")
                )

                self.results_table.setItem(row, 2, QTableWidgetItem(str(base)))

    # -----------------------------
    # CLICK TABELA
    # -----------------------------

    def table_clicked(self, row, column):

        code_item = self.results_table.item(row, 0)
        path_item = self.results_table.item(row, 2)

        if not code_item or not path_item:
            return

        code = code_item.text()
        path = Path(path_item.text())

        if column == 2:
            if path.exists():
                os.startfile(path)

            return

        if code in self.found:
            step_path = self.found[code]

            if step_path.exists():
                self.current_file_path = str(step_path)

                self.render_step(step_path)

    # -----------------------------
    # RENDER
    # -----------------------------

    def render_step(self, step_path):

        try:
            mesh = step_to_pyvista_mesh(step_path)

            mesh.compute_normals(
                cell_normals=False,
                point_normals=True,
                auto_orient_normals=True,
                inplace=True,
            )

            self.plotter.clear()

            self.plotter.add_mesh(
                mesh,
                color="lightgray",
                smooth_shading=True,
                show_edges=False,
                specular=0.7,
                specular_power=30,
            )

            self.plotter.enable_anti_aliasing()
            self.plotter.enable_lightkit()

            self.plotter.isometric_view()
            self.plotter.reset_camera()

            self.plotter.render()

            self.btn_print.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar STEP:\n{e}")

    # -----------------------------
    # LOAD STEP
    # -----------------------------

    def load_step(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Abrir STEP", "", "STEP Files (*.step *.stp)"
        )

        if not file_path:
            return

        self.current_file_path = file_path

        self.render_step(file_path)

    # -----------------------------
    # PRINTS
    # -----------------------------

    def batch_print(self):

        if not self.found:
            QMessageBox.warning(self, "Aviso", "Nenhum desenho encontrado.")
            return

        out_dir = Path(r"\\10.120.20.10\Departamento\Engenharia\07 - DESENHOS\3D")

        if not out_dir.exists():
            QMessageBox.critical(
                self, "Erro", f"A pasta de destino não existe:\n{out_dir}"
            )
            return

        for code, path in self.found.items():
            self.render_step(path)

            out = out_dir / f"{code}.png"

            self.plotter.screenshot(str(out))

        QMessageBox.information(self, "Concluído", f"Prints salvos em:\n{out_dir}")

    def take_screenshot(self):

        self.btn_print.setEnabled(False)

        try:
            if self.current_file_path:
                base = os.path.splitext(os.path.basename(self.current_file_path))[0]
                suggested = f"{base}_iso.png"
            else:
                suggested = "peca_isometrica.png"

            save_path, _ = QFileDialog.getSaveFileName(
                self, "Guardar Print", suggested, "Images (*.png)"
            )

            if not save_path:
                return

            self.plotter.render()

            self.plotter.screenshot(save_path)

            QMessageBox.information(
                self,
                "Sucesso",
                f"Imagem guardada em:\n{save_path}",
            )

        finally:
            self.btn_print.setEnabled(True)

    def copy_missing(self):

        lines = []

        for row in range(self.results_table.rowCount()):
            code_item = self.results_table.item(row, 0)
            status_item = self.results_table.item(row, 1)
            path_item = self.results_table.item(row, 2)

            if not code_item or not status_item or not path_item:
                continue

            status = status_item.text()

            if "não encontrado" in status or "pasta encontrada" in status:
                code = code_item.text()
                path = path_item.text()

                lines.append(f"{code}, {path}")

        if not lines:
            QMessageBox.information(
                self,
                "Info",
                "Nenhum desenho faltando.",
            )
            return

        text = "Gerar STEP dos arquivos abaixo\n\n" + "\n".join(lines)

        QApplication.clipboard().setText(text)

        QMessageBox.information(
            self,
            "Copiado",
            f"{len(lines)} itens copiados para área de transferência.",
        )

    def closeEvent(self, event):

        try:
            if self.plotter:
                self.plotter.clear()

                if self.plotter.ren_win:
                    self.plotter.ren_win.Finalize()

                self.plotter.close()

        except Exception:
            pass

        event.accept()


if __name__ == "__main__":
    myappid = (
        f"{DOMINIMO.lower()}.{APP_TITLE.replace(' ', '').lower()}.{VERSION.lower()}"
    )
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QApplication(sys.argv)
    caminho_icone = get_resource_path("logo.ico")
    app.setWindowIcon(QIcon(caminho_icone))
    window = CadViewer()
    window.show()
    sys.exit(app.exec())
