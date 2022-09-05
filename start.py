#GUI imports
import pickle
import pprint
import re
import shutil
import socket
import sys
from time import sleep
from typing import Any

from PyQt5.QtCore import Qt, QFile, QObject, pyqtSignal, QThread
from PyQt5.QtOpenGL import QGLWidget, QGLFormat, QGL
from PyQt5.QtSvg import QGraphicsSvgItem, QSvgRenderer
from PyQt5.QtWidgets import QGridLayout, QLabel, QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QSpacerItem, \
    QSizePolicy, QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem, QLineEdit
from PyQt5.QtGui import QPixmap, QCursor, QImage, QIcon, QPalette, QColor, QPainter, QBrush, QPen
from PyQt5 import QtCore, QtSvg
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QStackedLayout
import requests
import random
import asyncio
import aiohttp
from typing import Callable, Coroutine, List
import images_qr
import pymongo


client = pymongo.MongoClient("mongodb+srv://dbUser:8624@cluster0.dfylnsx.mongodb.net/?retryWrites=true&w=majority")
db = client["trivia-app"]
servers = db.servers
print(servers)


pokemons_with_sprites = []
pokemons_count = 0


async def http_get(session: aiohttp.ClientSession, url: str) -> Coroutine:
    global pokemons_count
    global pokemons_with_sprites
    """Execute an GET http call async """
    async with session.get(url) as response:
        pokemon = await response.json()
    # Storing only pokemon registers that have svg
    if pokemon["sprites"]["other"]["dream_world"]["front_default"]:
        pokemons_with_sprites.append(pokemon)
        pokemons_count += 1
    # print(f"{pokemons_count=}")
    return pokemon


async def fetch_pokemons(pokemons: List, http_get: Callable):
    """Gather many HTTP call made async """
    async with aiohttp.ClientSession() as session:
        tasks = []
        index = 0
        while index < len(pokemons):
            tasks.append(http_get(session, pokemons[index]["url"]))
            # print(index)
            index += 1
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        return responses


def run():
    with requests.get("https://pokeapi.co/api/v2/pokemon?limit=1154") as request:
        # read JSON file & extract data
        data = request.json()
        pokemons = data["results"]
    responses = asyncio.get_event_loop().run_until_complete(fetch_pokemons(pokemons, http_get))
    # print(responses)


run()

pokemons = random.sample(pokemons_with_sprites, 40)
index = 0
questions = []
while index < len(pokemons):
    rand_int = random.choice(range(index, index + 4))
    mystery_pokemon = pokemons[rand_int]
    pokemon_options = [
        pokemons[index]["name"], pokemons[index + 1]["name"], pokemons[index + 2]["name"], pokemons[index + 3]["name"]
    ]
    questions.append(
        {
            "mystery_pokemon_name":  mystery_pokemon["name"],
            "mystery_pokemon_img": mystery_pokemon["sprites"]["other"]["dream_world"]["front_default"],
            "pokemon_options": pokemon_options
        }
    )
    index += 4


# pprint.pprint(questions)
print("Done with request!")


class SvgView(QGraphicsView):
    Native, OpenGL, Image = range(3)

    def __init__(self, parent=None):
        super(SvgView, self).__init__(parent)

        self.renderer = SvgView.Native
        self.svgItem = None
        self.backgroundItem = None
        self.outlineItem = None
        self.image = QImage()

        self.setScene(QGraphicsScene(self))
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        # Prepare background check-board pattern.
        tilePixmap = QPixmap(64, 64)
        tilePixmap.fill(Qt.white)
        tilePainter = QPainter(tilePixmap)
        color = QColor(220, 220, 220)
        tilePainter.fillRect(0, 0, 32, 32, color)
        tilePainter.fillRect(32, 32, 32, 32, color)
        tilePainter.end()

        self.setBackgroundBrush(QBrush(tilePixmap))

    def drawBackground(self, p, rect):
        p.save()
        p.resetTransform()
        p.drawTiledPixmap(self.viewport().rect(),
                self.backgroundBrush().texture())
        p.restore()

    def openFile(self, svg_file):
        if not svg_file.exists():
            return

        s = self.scene()

        if self.backgroundItem:
            drawBackground = self.backgroundItem.isVisible()
        else:
            drawBackground = False

        if self.outlineItem:
            drawOutline = self.outlineItem.isVisible()
        else:
            drawOutline = True

        s.clear()
        self.resetTransform()

        self.svgItem = QGraphicsSvgItem(svg_file.fileName())
        self.svgItem.setFlags(QGraphicsItem.ItemClipsToShape)
        self.svgItem.setCacheMode(QGraphicsItem.NoCache)
        self.svgItem.setZValue(0)

        self.backgroundItem = QGraphicsRectItem(self.svgItem.boundingRect())
        self.backgroundItem.setBrush(Qt.white)
        self.backgroundItem.setPen(QPen(Qt.NoPen))
        self.backgroundItem.setVisible(drawBackground)
        self.backgroundItem.setZValue(-1)

        self.outlineItem = QGraphicsRectItem(self.svgItem.boundingRect())
        outline = QPen(Qt.black, 2, Qt.DashLine)
        outline.setCosmetic(True)
        self.outlineItem.setPen(outline)
        self.outlineItem.setBrush(QBrush(Qt.NoBrush))
        self.outlineItem.setVisible(drawOutline)
        self.outlineItem.setZValue(1)

        s.addItem(self.backgroundItem)
        s.addItem(self.svgItem)
        s.addItem(self.outlineItem)

        s.setSceneRect(self.outlineItem.boundingRect().adjusted(-10, -10, 10, 10))

    def setRenderer(self, renderer):
        self.renderer = renderer

        if self.renderer == SvgView.OpenGL:
            if QGLFormat.hasOpenGL():
                self.setViewport(QGLWidget(QGLFormat(QGL.SampleBuffers)))
        else:
            self.setViewport(QWidget())

    def setHighQualityAntialiasing(self, highQualityAntialiasing):
        if QGLFormat.hasOpenGL():
            self.setRenderHint(QPainter.HighQualityAntialiasing,
                    highQualityAntialiasing)

    def setViewBackground(self, enable):
        if self.backgroundItem:
            self.backgroundItem.setVisible(enable)

    def setViewOutline(self, enable):
        if self.outlineItem:
            self.outlineItem.setVisible(enable)

    def paintEvent(self, event):
        if self.renderer == SvgView.Image:
            if self.image.size() != self.viewport().size():
                self.image = QImage(self.viewport().size(),
                        QImage.Format_ARGB32_Premultiplied)

            imagePainter = QPainter(self.image)
            QGraphicsView.render(self, imagePainter)
            imagePainter.end()

            p = QPainter(self.viewport())
            p.drawImage(0, 0, self.image)
        else:
            super(SvgView, self).paintEvent(event)

    def wheelEvent(self, event):
        factor = pow(1.2, event.delta() / 240.0)
        self.scale(factor, factor)
        event.accept()


class Question(QWidget):

    print("Question: Out of __init__")

    score: int = 0
    index: int = 0

    def __init__(self):
        # self.index = 0
        self.aciertos = 0
        self.desaciertos = 0
        self.viewer = QtSvg.QSvgWidget()
        self.get_svg_size = QSvgRenderer('mystery_pokemon.svg')
        self.v_layout = QVBoxLayout()
        self.grid = QGridLayout()
        # self.view = SvgView()
        super(Question, self).__init__()
        print("Question Init")
        self.set_ui()
        print("Adding vertical layout layout...")
        # self.destroy(True)
        self.setLayout(self.v_layout)

    def create_button(self, option, l_margin, r_margin):
        button = QPushButton(option)
        button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        button.setFixedWidth(485)
        button.setStyleSheet(
            # setting variable margins
            """
                *{
                    margin-left: %d px;
                    margin-right: %d px;
                    border: 4px solid '#BBE6FA';
                    color: #BBE6FA;
                    font-family: 'shanti';
                    font-size: 16px;
                    border-radius: 25px;
                    padding: 15px 0;
                    margin-top: 20px;
                }
                *:hover{
                    background: '#BBE6FA';
                    color: '#171D20'
                }
            """ % (l_margin, r_margin)
        )
        button.clicked.connect(lambda: self.is_correct(button))
        return button

    def load_img(self):
        print(questions[self.index]["mystery_pokemon_img"])
        r = requests.get(questions[self.index]["mystery_pokemon_img"], stream=True)
        if r.status_code == 200:
            with open("mystery_pokemon.svg", 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)

        with open("mystery_pokemon.svg", 'rb') as f:
            svg_content = f.read()
        with open("mystery_pokemon.svg", 'wb') as f:
            f.write(re.sub(b"#[0-9a-z]{6}", b"#FFFFFF", svg_content))

        self.viewer.load('mystery_pokemon.svg')
        self.viewer.setFixedSize(self.get_svg_size.defaultSize())

    def set_ui(self):
        print("Set UI")
        print(f"{self.index=}")
        print(f"{self.score=}")
        print(f"{questions[self.index]['mystery_pokemon_name']=}")
        self.score_label = QLabel(str(self.score))
        self.score_label.setAlignment(QtCore.Qt.AlignRight)
        self.score_label.setStyleSheet(
            '''
            font-size: 35px;
            color: 'white';
            padding: 15px 10px;
            margin: 20px 200px;
            background: '#64A314';
            border: 1px solid '#64A314';
            border-radius: 35px;
            '''
        )

        self.load_img()

        self.button1 = self.create_button(questions[self.index]["pokemon_options"][0], 85, 5)
        self.button2 = self.create_button(questions[self.index]["pokemon_options"][1], 5, 85)
        self.button3 = self.create_button(questions[self.index]["pokemon_options"][2], 85, 5)
        self.button4 = self.create_button(questions[self.index]["pokemon_options"][3], 5, 85)

        # self.buttons = [QPushButton(questions[self.index]["pokemon_options"][i]) for i in range(4)]
        # i = 0
        # print(self.buttons)
        # while i < len(self.buttons):
        #     self.buttons[i].setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        #     self.buttons[i].setFixedWidth(485)
        #     l_margin, r_margin = (85, 5) if i % 2 == 0 else (5, 85)
        #     self.buttons[i].setStyleSheet(
        #         # setting variable margins
        #         """
        #             *{
        #                 margin-left: %d px;
        #                 margin-right: %d px;
        #                 border: 4px solid '#BBE6FA';
        #                 color: #BBE6FA;
        #                 font-family: 'shanti';
        #                 font-size: 16px;
        #                 border-radius: 25px;
        #                 padding: 15px 0;
        #                 margin-top: 20px;
        #             }
        #             *:hover{
        #                 background: '#BBE6FA';
        #                 color: '#171D20'
        #             }
        #         """ % (l_margin, r_margin)
        #     )
        #     print(i)
        #     self.buttons[i].clicked.connect(lambda: self.is_correct(self.buttons[i]))
        #     i += 1
        # i = 0
        # for i, button in enumerate(buttons):
        #     button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        #     button.setFixedWidth(485)
        #     l_margin, r_margin = (85, 5) if i % 2 == 0 else (5, 85)
        #     button.setStyleSheet(
        #         # setting variable margins
        #         """
        #             *{
        #                 margin-left: %d px;
        #                 margin-right: %d px;
        #                 border: 4px solid '#BBE6FA';
        #                 color: #BBE6FA;
        #                 font-family: 'shanti';
        #                 font-size: 16px;
        #                 border-radius: 25px;
        #                 padding: 15px 0;
        #                 margin-top: 20px;
        #             }
        #             *:hover{
        #                 background: '#BBE6FA';
        #                 color: '#171D20'
        #             }
        #         """ % (l_margin, r_margin)
        #     )
        #     button.clicked.connect(lambda: self.is_correct(button))

        image = QPixmap(":/Images/classic_pokemon_logo.png")
        logo = QLabel()
        logo.setPixmap(image)
        logo.setAlignment(QtCore.Qt.AlignCenter)
        logo.setStyleSheet("margin-top: 75px; margin-bottom: 30px;")

        self.v_layout.addWidget(self.score_label, Qt.AlignRight)
        # self.grid.addWidget(self.mystery_label, 1, 0, 1, 2)
        self.v_layout.addWidget(self.viewer, Qt.AlignCenter, Qt.AlignCenter)
        self.grid.addWidget(self.button1, 0, 0)
        self.grid.addWidget(self.button2, 0, 1)
        self.grid.addWidget(self.button3, 1, 0)
        self.grid.addWidget(self.button4, 1, 1)
        self.v_layout.addLayout(self.grid)
        self.v_layout.addWidget(logo, Qt.AlignCenter, Qt.AlignCenter)

        # svg_file = QFile("mystery_pokemon.svg")
        # self.view.openFile(svg_file)

    def is_correct(self, button):
        if button.text() == questions[self.index]["mystery_pokemon_name"]:
            self.score += 10
            self.aciertos += 1
            self.score_label.setText(str(self.score))
        else:
            self.desaciertos += 1
        if self.score == 100 or self.index == 9:
            print(f"{self.score=}")
            print("Game Over")
            final_score_widget.final_score_holder.setText(f"Score: {self.score}")
            final_score_widget.aciertos_holder.setText(f"Correct: {self.aciertos}")
            final_score_widget.desaciertos_holder.setText(f"Incorrect: {self.desaciertos}")
            print(final_score_widget.final_score_holder.text())
            window.stacklayout.setCurrentIndex(4)
        else:
            print(f"{button.text()=}")
            self.index += 1
            # img_data = requests.get(questions[self.index]["mystery_pokemon_img"]).content
            # self.mystery_pokemon_holder.loadFromData(img_data)
            # self.mystery_label.setPixmap(QPixmap(self.mystery_pokemon_holder))
            self.load_img()
            # svg_file = QFile("mystery_pokemon.svg")
            # self.view.openFile(svg_file)
            self.button1.setText(questions[self.index]["pokemon_options"][0])
            self.button2.setText(questions[self.index]["pokemon_options"][1])
            self.button3.setText(questions[self.index]["pokemon_options"][2])
            self.button4.setText(questions[self.index]["pokemon_options"][3])
            print(f"{questions[self.index]['mystery_pokemon_name']=}")
            # self.buttons = [QPushButton(questions[self.index]["pokemon_options"][i]) for i in range(4)]
            # Question(self.index, self.score).show()
            # self.set_ui()


class FinalScores(QWidget):

    print("FinalScores: Out of __init__")

    def __init__(self):
        print("FinalScores Init")
        super(FinalScores, self).__init__()
        v_layout = QVBoxLayout()
        verticalSpacer = QSpacerItem(0, 0, hPolicy=QSizePolicy.Minimum, vPolicy=QSizePolicy.Expanding)
        verticalSpacer2 = QSpacerItem(0, 0, hPolicy=QSizePolicy.Minimum, vPolicy=QSizePolicy.Expanding)
        self.final_score_holder = QLabel()
        self.final_score_holder.setAlignment(Qt.AlignCenter)
        self.final_score_holder.setStyleSheet(
            '''
            *{
                font: Bahnschrift SemiBold;
                font-size: 100px;
                color: '#BBE6FA'; 
                /* padding: 25px 0; */
                /* margin: 10px 200px; */
            }
            '''
        )
        self.aciertos_holder = QLabel()
        self.aciertos_holder.setAlignment(Qt.AlignCenter)
        self.aciertos_holder.setStyleSheet(
            '''
            *{
                font: Bahnschrift Light;
                font-size: 50px;
                color: '#BBE6FA'; 
                /* padding: 25px 0; */
                /* margin: 10px 200px; */
            }
            '''
        )
        self.desaciertos_holder = QLabel()
        self.desaciertos_holder.setAlignment(Qt.AlignCenter)
        self.desaciertos_holder.setStyleSheet(
            '''
            *{
                font: Bahnschrift Light;
                font-size: 50px;
                color: '#BBE6FA'; 
                /* padding: 25px 0; */
                /* margin: 10px 200px; */
            }
            '''
        )
        v_layout.addItem(verticalSpacer)
        v_layout.addWidget(self.final_score_holder)
        v_layout.addWidget(self.aciertos_holder)
        v_layout.addWidget(self.desaciertos_holder)
        v_layout.addItem(verticalSpacer2)
        v_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.setLayout(v_layout)

class JoinGame(QWidget):

    print("FinalScores: Out of __init__")

    def __init__(self):
        print("FinalScores Init")
        super(JoinGame, self).__init__()
        v_layout = QVBoxLayout()
        verticalSpacer = QSpacerItem(0, 0, hPolicy=QSizePolicy.Minimum, vPolicy=QSizePolicy.Expanding)
        verticalSpacer2 = QSpacerItem(0, 0, hPolicy=QSizePolicy.Minimum, vPolicy=QSizePolicy.Expanding)
        self.server: dict
        self.pin_label = QLabel("PIN")
        self.pin_label.setAlignment(Qt.AlignCenter)
        self.pin_label.setStyleSheet(
            '''
            *{
                font: Bahnschrift SemiBold;
                font-size: 100px;
                color: '#BBE6FA'; 
                /* padding: 25px 0; */
                /* margin: 10px 200px; */
            }
            '''
        )
        self.pin_input = QLineEdit()
        self.pin_input.setAlignment(Qt.AlignCenter)
        self.pin_input.setStyleSheet(
            """
                *{
                    margin-left: %d px;
                    margin-right: %d px;
                    border: 4px solid '#BBE6FA';
                    font-family: 'shanti';
                    font-size: 100px;
                    color: white;
                    border-radius: 50px;
                    padding: 15px 0;
                    margin-top: 20px;
                }/*
                *:hover{
                    background: '#BBE6FA';
                    color: '#171D20'
                }*/
            """ % (85, 5)
        )
        self.pin_input.returnPressed.connect(self.exec_long_task)
        v_layout.addItem(verticalSpacer)
        v_layout.addWidget(self.pin_label)
        v_layout.addWidget(self.pin_input)
        v_layout.addItem(verticalSpacer2)
        v_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.setLayout(v_layout)

    def exec_long_task(self):
        # Step 2: Create a QThread object
        self.thread = QThread()
        # Step 3: Create a worker object
        self.worker = Worker2()
        # Step 4: Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Step 5: Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # Step 6: Start the thread
        self.thread.start()

        self.thread.finished.connect(
            lambda: print(
                join_game_widget.server
            )
        )

        self.thread.finished.connect(
            lambda: self.recieve_questions()
        )

        self.thread.finished.connect(
            lambda: trivia_menu_widget.show_question_panel()
        )

    def recieve_questions(self):
        # Establecemos el tipo de socket/conexion
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = 5000  # Puerto de comunicacion
        # Realizamos la conexion al la IP y puerto
        sock.connect((join_game_widget.server["IP"], port))
        # Leemos los datos del servidor
        data = sock.recv(20480)
        data = pickle.loads(data)
        # Cerramos el socket
        sock.close()
        # Mostramos los datos recibidos
        print(data)


class Worker2(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def run(self):
        """Long-running task."""
        join_game_widget.server = servers.find_one({"PIN": join_game_widget.pin_input.text()})
        self.finished.emit()


class CreateGame(QWidget):

    print("FinalScores: Out of __init__")

    def __init__(self):
        print("FinalScores Init")
        super(CreateGame, self).__init__()
        v_layout = QVBoxLayout()
        verticalSpacer = QSpacerItem(0, 0, hPolicy=QSizePolicy.Minimum, vPolicy=QSizePolicy.Expanding)
        verticalSpacer2 = QSpacerItem(0, 0, hPolicy=QSizePolicy.Minimum, vPolicy=QSizePolicy.Expanding)
        self.pin_label = QLabel("PIN")
        self.pin_label.setAlignment(Qt.AlignCenter)
        self.pin_label.setStyleSheet(
            '''
            *{
                font: Bahnschrift SemiBold;
                font-size: 100px;
                color: '#BBE6FA'; 
                /* padding: 25px 0; */
                /* margin: 10px 200px; */
            }
            '''
        )
        self.pin_holder = QLabel()
        self.pin_holder.setAlignment(Qt.AlignCenter)
        self.pin_holder.setStyleSheet(
            '''
            *{
                font: Bahnschrift Light;
                font-size: 50px;
                color: '#BBE6FA'; 
                /* padding: 25px 0; */
                /* margin: 10px 200px; */
            }
            '''
        )
        v_layout.addItem(verticalSpacer)
        v_layout.addWidget(self.pin_label)
        v_layout.addWidget(self.pin_holder)
        v_layout.addItem(verticalSpacer2)
        v_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.setLayout(v_layout)


class TriviaMenu(QWidget):

    print("TriviaMenu: Out of __init__")

    def __init__(self):
        print("TriviaMenu Init")
        super(TriviaMenu, self).__init__()
        verticalSpacer = QSpacerItem(0, 0, hPolicy=QSizePolicy.Minimum, vPolicy=QSizePolicy.Expanding)
        verticalSpacer2 = QSpacerItem(0, 0, hPolicy=QSizePolicy.Minimum, vPolicy=QSizePolicy.Expanding)
        horizontalSpacer = QSpacerItem(0, 0, hPolicy=QSizePolicy.Fixed, vPolicy=QSizePolicy.Minimum)
        horizontalSpacer2 = QSpacerItem(0, 0, hPolicy=QSizePolicy.Fixed, vPolicy=QSizePolicy.Minimum)
        v_layout = QVBoxLayout()
        image = QPixmap("Images/classic_pokemon_logo.png")
        logo = QLabel()
        logo.setPixmap(image)
        logo.setAlignment(QtCore.Qt.AlignCenter)
        # logo.setStyleSheet("margin-top: 100px;")
        logo.setStyleSheet("margin-bottom: 75px;")
        join_game_button = QPushButton("Join Game")
        create_game_button = QPushButton("Create Game")
        game_button_stylesheet = '''
            *{
                border: 4px solid '#BBE6FA';
                border-radius: 25px;
                font-size: 35px;
                color: '#BBE6FA';
                padding: 25px 0;
                margin-bottom: 10px;
                /* margin-right: 200px; */
                /* margin-left: 200px; */
            }
            *:hover{
                background: '#BBE6FA';
                color: '#171D20'
            }
        '''
        join_game_button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        create_game_button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))

        join_game_button.setStyleSheet(game_button_stylesheet)
        create_game_button.setStyleSheet(game_button_stylesheet)
        join_game_button.setFixedWidth(500)
        create_game_button.setFixedWidth(500)

        join_game_button.clicked.connect(self.show_join_game_panel)
        create_game_button.clicked.connect(self.exec_long_task)

        # join_game_button.clicked.connect(self.show_question_panel)

        v_layout.addItem(verticalSpacer)

        v_layout.addWidget(logo)
        button_group_layout = QVBoxLayout()
        button_group_layout.addWidget(join_game_button)
        button_group_layout.addWidget(create_game_button)
        button_section_layout = QHBoxLayout()
        button_section_layout.addItem(horizontalSpacer)
        button_section_layout.addLayout(button_group_layout)
        button_section_layout.addItem(horizontalSpacer2)
        button_section_widget = QWidget()
        button_section_widget.setLayout(button_section_layout)
        v_layout.addWidget(button_section_widget)
        # v_layout.addLayout(button_group_layout)

        v_layout.addItem(verticalSpacer2)

        # v_layout.addWidget(join_game_button)
        # v_layout.addWidget(create_game_button)

        self.setLayout(v_layout)

    def exec_long_task(self):
        # Step 2: Create a QThread object
        self.thread = QThread()
        # Step 3: Create a worker object
        self.worker = Worker()
        self.worker3 = Worker3()
        # Step 4: Move worker to the thread
        self.worker.moveToThread(self.thread)
        self.worker3.moveToThread(self.thread)
        # Step 5: Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker3.finished.connect(self.thread.quit)
        self.worker3.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # Step 6: Start the thread
        self.thread.start()

        self.thread.finished.connect(
            lambda: self.show_create_game_panel()
        )

    def show_join_game_panel(self):
        window.stacklayout.setCurrentIndex(1)

    def show_create_game_panel(self):
        window.stacklayout.setCurrentIndex(2)

    def show_question_panel(self):
        window.stacklayout.setCurrentIndex(3)


class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def run(self):
        """Long-running task."""
        pin = "".join([str(random.randint(0, 9)) for i in range(6)])
        create_game_widget.pin_holder.setText(pin)
        print("PIN generated")
        result = servers.insert_one({
            "IP": socket.gethostbyname(socket.gethostname()),
            "PIN": pin
        })
        print(result)
        self.finished.emit()


class Worker3(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def run(self):
        # Establecemos el tipo de socket/conexion
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = 5000  # Puerto de comunicacion
        sock.bind((join_game_widget.server["IP"], port))  # IP y Puerto de conexion en una Tupla

        print("esperando conexiones en el puerto ", port)
        # Vamos a esperar que un cliente se conecte
        # Mientras tanto el script se va a pausar
        sock.listen(1)
        # Cuando un cliente se conecte vamos a obtener la client_addr osea la direccion
        # tambien vamos a obtener la con, osea la conexion que servira para enviar datos y recibir datos
        con, client_addr = sock.accept()
        data = pickle.dumps(questions)
        con.send(data)
        con.close()
        sock.close()
        self.finished.emit()


class MainWindow(QMainWindow):

    print("MainWindow: Out of __init__")
    stacklayout = QStackedLayout()
    # trivia_menu_widget: Any
    # question_widget: Any
    # final_score_widget: Any

    def __init__(self):
        print("MainWindow Init")
        super().__init__()
        self.setWindowTitle("Pokemon Trivia")
        self.setWindowIcon(QIcon(":/Images/poke.png"))

        pagelayout = QVBoxLayout()
        pagelayout.addLayout(self.stacklayout)

        self.stacklayout.addWidget(trivia_menu_widget)
        self.stacklayout.addWidget(join_game_widget)
        self.stacklayout.addWidget(create_game_widget)
        self.stacklayout.addWidget(question_widget)
        self.stacklayout.addWidget(final_score_widget)

        self.stacklayout.setCurrentIndex(0)

        widget = QWidget()
        widget.setLayout(pagelayout)
        # widget.setStyleSheet(
        #     """
        #     * {
        #         margin: 10px 200px 100px;
        #     }
        #     """
        # )
        self.setCentralWidget(widget)


app = QApplication(sys.argv)
create_game_widget = CreateGame()
join_game_widget = JoinGame()
trivia_menu_widget = TriviaMenu()
question_widget = Question()
final_score_widget = FinalScores()
window = MainWindow()
#place window in (x,y) coordinates
# window.move(2700, 200)
# window.setFixedWidth(1000)
# window.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
window.setMinimumSize(1000, 600)
window.setStyleSheet("background: #171D20;")
window.showMaximized()
window.show()
sys.exit(app.exec())
